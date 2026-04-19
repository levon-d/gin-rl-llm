package gin.util;

import com.sampullara.cli.Args;
import com.sampullara.cli.Argument;
import gin.Patch;
import gin.SourceFile;
import gin.edit.Edit;
import gin.edit.Edit.EditType;
import gin.rl.AbstractBanditSelector;
import gin.rl.OperatorSelector;
import gin.rl.OperatorSpace;
import gin.rl.UCBSelector;
import gin.rl.UniformSelector;
import gin.test.UnitTest;
import gin.test.UnitTestResultSet;
import org.apache.commons.rng.simple.JDKRandomBridge;
import org.apache.commons.rng.simple.RandomSource;
import org.pmw.tinylog.Logger;

import com.opencsv.CSVWriter;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.Serial;
import java.util.*;

/**
 * RL-guided Local Search for Memory Optimization.
 */
public class RLLocalSearchMemory extends GP {

    @Serial
    private static final long serialVersionUID = 1L;

    @Argument(alias = "rl", description = "RL algorithm: uniform or ucb (default: ucb)")
    protected String rlAlgorithm = "ucb";

    @Argument(alias = "ucbc", description = "Exploration constant for UCB (default: sqrt(2))")
    protected Double ucbC = Math.sqrt(2);

    @Argument(alias = "ops", description = "Operator set: traditional, llm, all (default: traditional)")
    protected String operatorSet = "traditional";

    @Argument(alias = "rllog", description = "RL-specific log file")
    protected String rlLogFile = "rl_operator_log.csv";

    private OperatorSelector operatorSelector;
    private List<Class<? extends Edit>> operators;
    private PrintWriter rlLogWriter;
    private Random rlRng;

    private int totalSteps = 0;
    private int improvingSteps = 0;

    private List<MethodMemoryResult> methodResults = new ArrayList<>();

    private static class MethodMemoryResult {
        String methodName;
        long baselineMemory;
        long bestMemory;
        String bestPatch;

        MethodMemoryResult(String name, long baseline, long best, String patch) {
            this.methodName = name;
            this.baselineMemory = baseline;
            this.bestMemory = best;
            this.bestPatch = patch;
        }

        double improvementPercent() {
            if (baselineMemory == 0) return 0;
            return 100.0 * (baselineMemory - bestMemory) / baselineMemory;
        }
    }

    public RLLocalSearchMemory(String[] args) {
        super(args);
        Args.parseOrExit(this, args);
        initializeRL();
    }

    public RLLocalSearchMemory(File projectDir, File methodFile) {
        super(projectDir, methodFile);
        initializeRL();
    }

    private void initializeRL() {
        this.operators = OperatorSpace.getOperatorsByCategory(operatorSet);

        this.rlRng = new JDKRandomBridge(RandomSource.MT, Long.valueOf(super.mutationSeed));
        this.operatorSelector = switch (rlAlgorithm.toLowerCase()) {
            case "uniform", "random" -> new UniformSelector(operators, rlRng);
            case "ucb", "ucb1" -> new UCBSelector(operators, ucbC, rlRng);
            default -> throw new IllegalArgumentException("Unknown RL algorithm: " + rlAlgorithm);
        };

        try {
            rlLogWriter = new PrintWriter(new FileWriter(rlLogFile, false));
            rlLogWriter.println("MethodID,Step,Operator,Success,ParentMemory(KB),ChildMemory(KB),Reward");
        } catch (IOException e) {
            Logger.error("Failed to create RL log file: " + e.getMessage());
        }

        Logger.info("=== RLLocalSearchMemory ===");
        Logger.info("RL Algorithm: " + rlAlgorithm);
        Logger.info("UCB c: " + ucbC);
        Logger.info("Operators: " + operators.size() + " (" + operatorSet + ")");
        Logger.info("===========================");
    }

    /**
     * Override header to explicitly show memory units.
     */
    @Override
    protected void writeNewHeader() {
        String[] entry = { "MethodName"
                , "Iteration"
                , "EvaluationNumber"
                , "Patch"
                , "Compiled"
                , "AllTestsPassed"
                , "TotalExecutionTime(ms)"
                , "Memory(KB)"
                , "MemoryImprovement(KB)"
        };
        try {
            outputFileWriter = new CSVWriter(new FileWriter(outputFile));
            outputFileWriter.writeNext(entry);
        } catch (IOException e) {
            Logger.error(e, "Exception writing results to the output file: " + outputFile.getAbsolutePath());
            Logger.trace(e);
            System.exit(-1);
        }
    }

    public static void main(String[] args) {
        RLLocalSearchMemory search = new RLLocalSearchMemory(args);
        search.sampleMethods();
        search.printFinalSummary();
    }

    @Override
    protected UnitTestResultSet initFitness(String className, List<UnitTest> tests, Patch origPatch) {
        return testPatch(className, tests, origPatch, null);
    }

    @Override
    protected double fitness(UnitTestResultSet results) {
        if (results.getCleanCompile() && results.allTestsSuccessful()) {
            return (double) results.totalMemoryUsage();
        }
        return Double.MAX_VALUE;
    }

    @Override
    protected boolean fitnessThreshold(UnitTestResultSet results, double orig) {
        return results.allTestsSuccessful();
    }

    @Override
    protected double compareFitness(double newFitness, double oldFitness) {
        return oldFitness - newFitness;
    }

    @Override
    protected void search(TargetMethod method, Patch origPatch) {
        Logger.info("Running RL-guided local search with " + rlAlgorithm.toUpperCase());

        String className = method.getClassName();
        String methodName = method.toString();
        List<UnitTest> tests = method.getGinTests();
        Integer methodID = method.getMethodID();

        UnitTestResultSet results = initFitness(className, tests, origPatch);
        double origFitness = fitness(results);
        super.writePatch(-1, 0, results, methodName, origFitness, 0);

        Logger.info("Original memory: " + (long) origFitness + " KB");

        double bestFitness = origFitness;
        Patch bestPatch = origPatch;

        if (operatorSelector instanceof AbstractBanditSelector bandit) {
            bandit.reset();
        }

        for (int step = 1; step < super.indNumber; step++) {
            totalSteps++;

            Class<? extends Edit> selectedOperator = operatorSelector.select();

            Patch neighbour = createNeighbour(bestPatch, selectedOperator);

            results = testPatch(className, tests, neighbour, null);
            double newFitness = fitness(results);

            boolean success = results.getCleanCompile() && results.allTestsSuccessful();
            double reward = calculateReward(bestFitness, newFitness, success);

            operatorSelector.updateQuality(selectedOperator, (long) bestFitness,
                    success ? (long) newFitness : null, success);

            logRLStep(methodID, step, selectedOperator, success, bestFitness, newFitness, reward);

            double improvement = compareFitness(newFitness, origFitness);
            super.writePatch(step, step, results, methodName, newFitness, improvement);

            if (success && newFitness < bestFitness) {
                bestFitness = newFitness;
                bestPatch = neighbour;
                improvingSteps++;

                double pctImprovement = 100.0 * (origFitness - bestFitness) / origFitness;
                Logger.info(String.format("Step %d: NEW BEST - %d KB (%.1f%% improvement) using %s",
                        step, (long) bestFitness, pctImprovement, selectedOperator.getSimpleName()));
            } else {
                Logger.debug(String.format("Step %d: %s - %s",
                        step, selectedOperator.getSimpleName(),
                        success ? "no improvement" : "failed"));
            }
        }

        double finalImprovement = 100.0 * (origFitness - bestFitness) / origFitness;
        Logger.info(String.format("Method %s: Original=%d, Best=%d (%.1f%% improvement)",
                methodName, (long) origFitness, (long) bestFitness, finalImprovement));

        methodResults.add(new MethodMemoryResult(
                methodName, (long) origFitness, (long) bestFitness, bestPatch.toString()));
    }

    private Patch createNeighbour(Patch patch, Class<? extends Edit> operatorClass) {
        Patch neighbour = patch.clone();
        if (neighbour.size() > 0 && super.mutationRng.nextFloat() > 0.5) {
            neighbour.remove(super.mutationRng.nextInt(neighbour.size()));
        } else {
            neighbour.addRandomEditOfClass(super.mutationRng, operatorClass);
        }

        return neighbour;
    }

    private double calculateReward(double parentFitness, double childFitness, boolean success) {
        if (!success || childFitness <= 0 || childFitness == Double.MAX_VALUE) {
            return 0.0;
        }
        return parentFitness / childFitness;
    }

    private void logRLStep(int methodID, int step, Class<? extends Edit> operator,
                           boolean success, double parentFitness, double childFitness, double reward) {
        if (rlLogWriter != null) {
            rlLogWriter.printf("%d,%d,%s,%b,%.0f,%.0f,%.4f%n",
                    methodID, step, operator.getSimpleName(), success,
                    parentFitness, childFitness == Double.MAX_VALUE ? -1 : childFitness, reward);
            rlLogWriter.flush();
        }
    }

    private void printFinalSummary() {
        Logger.info("=".repeat(60));
        Logger.info("RL Local Search Complete");
        Logger.info("=".repeat(60));
        Logger.info("Algorithm: " + rlAlgorithm.toUpperCase());
        Logger.info("Total steps: " + totalSteps);
        Logger.info("Improving steps: " + improvingSteps);
        if (totalSteps > 0) {
            Logger.info("Improvement rate: " + String.format("%.1f%%", 100.0 * improvingSteps / totalSteps));
        }
        Logger.info("RL log saved to: " + rlLogFile);

        String summaryFile = rlLogFile.replace("_rl_log", "_memory_summary")
                .replace(".csv", "_summary.csv");
        writeSummaryCSV(summaryFile);
        Logger.info("Memory summary saved to: " + summaryFile);
        Logger.info("=".repeat(60));

        if (rlLogWriter != null) {
            rlLogWriter.close();
        }
    }

    private void writeSummaryCSV(String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("MethodName,BaselineMemory(KB),BestMemory(KB),MemoryReduction(KB),ImprovementPercent,BestPatch");

            for (MethodMemoryResult result : methodResults) {
                long reduction = result.baselineMemory - result.bestMemory;
                String patchStr = result.bestPatch.replace(",", ";").replace("\"", "'");
                writer.printf("\"%s\",%d,%d,%d,%.2f,\"%s\"%n",
                        result.methodName,
                        result.baselineMemory,
                        result.bestMemory,
                        reduction,
                        result.improvementPercent(),
                        patchStr);
            }

            long totalBaseline = methodResults.stream().mapToLong(r -> r.baselineMemory).sum();
            long totalBest = methodResults.stream().mapToLong(r -> r.bestMemory).sum();
            long totalReduction = totalBaseline - totalBest;
            double totalPercent = totalBaseline > 0 ? 100.0 * totalReduction / totalBaseline : 0;
            writer.printf("\"TOTAL\",%d,%d,%d,%.2f,\"\"%n",
                    totalBaseline, totalBest, totalReduction, totalPercent);

        } catch (IOException e) {
            Logger.error("Failed to write summary CSV: " + e.getMessage());
        }
    }

    @Override
    protected List<Patch> select(Map<Patch, Double> population, Patch origPatch, double origFitness) {
        return new ArrayList<>();
    }

    @Override
    protected Patch mutate(Patch oldPatch) {
        Patch patch = oldPatch.clone();
        Class<? extends Edit> op = operatorSelector.select();
        patch.addRandomEditOfClass(super.mutationRng, op);
        return patch;
    }

    @Override
    protected List<Patch> crossover(List<Patch> patches, Patch origPatch) {
        return patches;
    }
}
