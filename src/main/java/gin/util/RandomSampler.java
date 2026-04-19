package gin.util;

import com.opencsv.CSVWriter;
import com.sampullara.cli.Args;
import com.sampullara.cli.Argument;
import gin.Patch;
import gin.SourceFile;
import gin.edit.Edit;
import gin.edit.Edit.EditType;
import gin.edit.llm.LLMMaskedStatement;
import gin.edit.llm.LLMReplaceStatement;
import gin.test.UnitTest;
import gin.test.UnitTestResultSet;

import org.apache.commons.rng.simple.JDKRandomBridge;
import org.apache.commons.rng.simple.RandomSource;
import org.pmw.tinylog.Logger;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.Serial;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.HashMap;
import java.util.Random;
import java.util.ArrayList;
import java.util.Arrays;


/**
 * Random sampler with runtime tracking.
 * <p>
 * Creates patchNumber random method patches of size 1:patchSize
 * and tracks runtime improvements per operator.
 */

public class RandomSampler extends Sampler {

    @Serial
    private static final long serialVersionUID = 5754760811598365140L;

    @Argument(alias = "et", description = "Edit type: this can be a member of the EditType enum (LINE,STATEMENT,MATCHED_STATEMENT,MODIFY_STATEMENT); the fully qualified name of a class that extends gin.edit.Edit, or a comma separated list of both")
    protected String editType = EditType.LINE.toString();

    @Argument(alias = "ps", description = "Number of edits per patch")
    protected Integer patchSize = 1;

    @Argument(alias = "pn", description = "Number of patches")
    protected Integer patchNumber = 10;

    @Argument(alias = "rm", description = "Random seed for method selection")
    protected Integer methodSeed = 123;

    @Argument(alias = "rp", description = "Random seed for edit type selection")
    protected Integer patchSeed = 123;

    @Argument(alias = "pb", description = "Probablity of combined")
    protected Double combinedProbablity = 0.5;

    private boolean ifLLM = false;
    private Class<? extends Edit> LLMedit = null;
    private List<Class<? extends Edit>> NoneLLMedit = new ArrayList<>();
    private Random mutationRng;

    // Allowed edit types for sampling: parsed from editType
    protected List<Class<? extends Edit>> editTypes;

    private Map<Integer, Double> baselineRuntime = new HashMap<>();
    private CSVWriter runtimeOutputWriter;

    private int totalPatches = 0;
    private int compilingPatches = 0;
    private int passingPatches = 0;
    private int improvingPatches = 0;
    private Map<String, int[]> operatorStats = new HashMap<>(); // [attempts, successes, improvements]

    public RandomSampler(String[] args) {
        super(args);
        Args.parseOrExit(this, args);
        editTypes = Edit.parseEditClassesFromString(editType);
        Setup();
        printAdditionalArguments();
    }

    private void Setup() {
        mutationRng = new JDKRandomBridge(RandomSource.MT, Long.valueOf(patchSeed));

        if (editTypes.contains(LLMMaskedStatement.class) || editTypes.contains(LLMReplaceStatement.class)) {
            ifLLM = true;
            if (editTypes.contains(LLMMaskedStatement.class)) {
                LLMedit = LLMMaskedStatement.class;
            } else if (editTypes.contains(LLMReplaceStatement.class)) {
                LLMedit = LLMReplaceStatement.class;
            }

            for (Class<? extends Edit> edit : editTypes) {
                if (edit != LLMedit) {
                    NoneLLMedit.add(edit);
                }
            }
        }

        for (Class<? extends Edit> editType : editTypes) {
            operatorStats.put(editType.getSimpleName(), new int[]{0, 0, 0});
        }

        Logger.info("=== RandomSampler with Runtime Tracking ===");
        Logger.info("Edit types: " + editTypes.size() + " operators");
        Logger.info("LLM edits enabled: " + ifLLM);
        Logger.info("==========================================");
    }

    // Constructor used for testing
    public RandomSampler(File projectDir, File methodFile) {
        super(projectDir, methodFile);
        editTypes = Edit.parseEditClassesFromString(editType);
        Setup();
    }

    public static void main(String[] args) {
        RandomSampler sampler = new RandomSampler(args);
        sampler.sampleMethods();
    }

    private void printAdditionalArguments() {
        Logger.info("Edit types: " + editTypes);
        Logger.info("Number of edits per patch: " + patchSize);
        Logger.info("Number of patches: " + patchNumber);
        Logger.info("Random seed for method selection: " + methodSeed);
        Logger.info("Random seed for edit type selection: " + patchSeed);
    }

    private Class<? extends Edit> addRandomEdit(Patch patch) {
        Class<? extends Edit> selectedEdit;

        if (ifLLM && NoneLLMedit.size() > 0) {
            if (mutationRng.nextFloat() > combinedProbablity) {
                selectedEdit = LLMedit;
                patch.addRandomEditOfClasses(mutationRng, Arrays.asList(LLMedit));
            } else {
                selectedEdit = NoneLLMedit.get(mutationRng.nextInt(NoneLLMedit.size()));
                patch.addRandomEditOfClass(mutationRng, selectedEdit);
            }
        } else {
            selectedEdit = editTypes.get(mutationRng.nextInt(editTypes.size()));
            patch.addRandomEditOfClass(mutationRng, selectedEdit);
        }

        return selectedEdit;
    }

    private void writeRuntimeHeader() {
        String parentDirName = outputFile.getParent();
        if (parentDirName == null) {
            parentDirName = ".";
        }
        File parentDir = new File(parentDirName);
        if (!parentDir.exists()) {
            parentDir.mkdirs();
        }

        String[] header = {
            "PatchIndex", "MethodName", "MethodID", "Operator", "Patch",
            "Compiled", "AllTestsPassed", "BaselineRuntime(ms)", "PatchRuntime(ms)",
            "RuntimeImprovement(ms)", "ImprovementPercent"
        };

        try {
            runtimeOutputWriter = new CSVWriter(new FileWriter(outputFile));
            runtimeOutputWriter.writeNext(header);
        } catch (IOException e) {
            Logger.error(e, "Exception writing header to output file: " + outputFile.getAbsolutePath());
            System.exit(-1);
        }
    }

    private void writeRuntimeResult(int patchIndex, String methodName, int methodID,
                                     String operator, String patch, boolean compiled,
                                     boolean passed, double baseline, double patchRuntime) {
        double improvement = baseline - patchRuntime;
        double improvementPct = baseline > 0 ? 100.0 * improvement / baseline : 0;

        String[] entry = {
            String.valueOf(patchIndex),
            methodName,
            String.valueOf(methodID),
            operator,
            patch,
            String.valueOf(compiled),
            String.valueOf(passed),
            String.format("%.2f", baseline),
            String.format("%.2f", patchRuntime),
            String.format("%.2f", improvement),
            String.format("%.2f", improvementPct)
        };

        runtimeOutputWriter.writeNext(entry);
    }

    @Override
    protected void sampleMethodsHook() {
        if (patchSize <= 0) {
            Logger.info("Number of edits must be greater than 0.");
            return;
        }

        writeRuntimeHeader();

        int numMethods = methodData.size();
        Logger.info("Number of methods: " + numMethods);
        Logger.info("Number of patches to generate: " + patchNumber);

        Logger.info("Getting baseline runtime for all methods...");
        for (TargetMethod method : methodData) {
            String className = method.getClassName();
            List<UnitTest> tests = method.getGinTests();
            Integer methodID = method.getMethodID();
            File source = method.getFileSource();

            SourceFile sourceFile = SourceFile.makeSourceFileForEditTypes(
                editTypes, source.getPath(), Collections.singletonList(method.getMethodName()));
            Patch emptyPatch = new Patch(sourceFile);

            UnitTestResultSet results = testPatch(className, tests, emptyPatch, null);
            double baseline = (double) (results.totalExecutionTime() / 1000000);
            baselineRuntime.put(methodID, baseline);

            Logger.info("Method " + method.getMethodName() + " (ID=" + methodID + "): baseline = " + baseline + " ms");
        }

        Logger.info("Generating and testing random patches...");
        Random mrng = new JDKRandomBridge(RandomSource.MT, Long.valueOf(methodSeed));

        for (int i = 0; i < patchNumber; i++) {
            totalPatches++;

            TargetMethod method = methodData.get(mrng.nextInt(numMethods));
            Integer methodID = method.getMethodID();
            String methodName = method.getMethodName();
            File source = method.getFileSource();
            String className = method.getClassName();
            List<UnitTest> tests = method.getGinTests();

            SourceFile sourceFile = SourceFile.makeSourceFileForEditTypes(
                editTypes, source.getPath(), Collections.singletonList(methodName));

            Patch patch = new Patch(sourceFile);
            List<String> usedOperators = new ArrayList<>();

            for (int j = 0; j < patchSize; j++) {
                Class<? extends Edit> editClass = addRandomEdit(patch);
                usedOperators.add(editClass.getSimpleName());
            }

            String operatorStr = String.join("+", usedOperators);

            UnitTestResultSet results = testPatch(className, tests, patch, null);
            boolean compiled = results.getCleanCompile();
            boolean passed = results.allTestsSuccessful();
            double patchRuntime = compiled && passed ? (double) (results.totalExecutionTime() / 1000000) : -1;
            double baseline = baselineRuntime.getOrDefault(methodID, 0.0);

            if (compiled) {
                compilingPatches++;
            }
            if (passed) {
                passingPatches++;
            }

            boolean improved = passed && patchRuntime >= 0 && patchRuntime < baseline;
            if (improved) {
                improvingPatches++;
            }

            if (patchSize == 1 && usedOperators.size() == 1) {
                String op = usedOperators.get(0);
                int[] stats = operatorStats.get(op);
                if (stats != null) {
                    stats[0]++; // attempts
                    if (passed) stats[1]++; // successes
                    if (improved) stats[2]++; // improvements
                }
            }

            writeRuntimeResult(i + 1, methodName, methodID, operatorStr,
                patch.toString(), compiled, passed, baseline, patchRuntime);

            if ((i + 1) % 100 == 0) {
                Logger.info("Progress: " + (i + 1) + "/" + patchNumber + " patches tested");
            }
        }

        try {
            runtimeOutputWriter.close();
        } catch (IOException e) {
            Logger.error("Failed to close output file");
        }

        Logger.info("Results saved to: " + outputFile);

        printSummary();
        writeSummaryCSV();
    }

    private void printSummary() {
        Logger.info("=".repeat(60));
        Logger.info("RANDOM SAMPLING SUMMARY");
        Logger.info("=".repeat(60));
        Logger.info("Total patches tested: " + totalPatches);
        Logger.info("Compiling patches: " + compilingPatches +
            " (" + String.format("%.1f", 100.0 * compilingPatches / totalPatches) + "%)");
        Logger.info("Test-passing patches: " + passingPatches +
            " (" + String.format("%.1f", 100.0 * passingPatches / totalPatches) + "%)");
        Logger.info("Runtime-improving patches: " + improvingPatches +
            " (" + String.format("%.1f", 100.0 * improvingPatches / totalPatches) + "%)");

        if (patchSize == 1) {
            Logger.info("");
            Logger.info("OPERATOR SUCCESS RATES (single-edit patches):");
            for (Map.Entry<String, int[]> entry : operatorStats.entrySet()) {
                int[] stats = entry.getValue();
                if (stats[0] > 0) {
                    double successRate = 100.0 * stats[1] / stats[0];
                    double improvementRate = 100.0 * stats[2] / stats[0];
                    Logger.info(String.format("  %s: %d attempts, %.1f%% pass, %.1f%% improve",
                        entry.getKey(), stats[0], successRate, improvementRate));
                }
            }
        }
        Logger.info("=".repeat(60));
    }

    private void writeSummaryCSV() {
        String summaryPath = outputFile.getAbsolutePath().replace(".csv", "_summary.csv");

        try (PrintWriter writer = new PrintWriter(new FileWriter(summaryPath))) {
            writer.println("Metric,Value,Percentage");
            writer.printf("TotalPatches,%d,100.00%n", totalPatches);
            writer.printf("CompilingPatches,%d,%.2f%n", compilingPatches, 100.0 * compilingPatches / totalPatches);
            writer.printf("PassingPatches,%d,%.2f%n", passingPatches, 100.0 * passingPatches / totalPatches);
            writer.printf("ImprovingPatches,%d,%.2f%n", improvingPatches, 100.0 * improvingPatches / totalPatches);
            writer.println();

            if (patchSize == 1) {
                writer.println("Operator,Attempts,Passes,PassRate,Improvements,ImprovementRate");
                for (Map.Entry<String, int[]> entry : operatorStats.entrySet()) {
                    int[] stats = entry.getValue();
                    if (stats[0] > 0) {
                        double passRate = 100.0 * stats[1] / stats[0];
                        double improvementRate = 100.0 * stats[2] / stats[0];
                        writer.printf("%s,%d,%d,%.2f,%d,%.2f%n",
                            entry.getKey(), stats[0], stats[1], passRate, stats[2], improvementRate);
                    }
                }
            }

            Logger.info("Summary saved to: " + summaryPath);
        } catch (IOException e) {
            Logger.error("Failed to write summary CSV: " + e.getMessage());
        }
    }
}
