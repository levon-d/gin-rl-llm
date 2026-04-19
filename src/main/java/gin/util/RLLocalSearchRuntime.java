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
import java.util.concurrent.*;

/**
 * RL-guided Local Search for Runtime Optimization.
 */
public class RLLocalSearchRuntime extends GP {

    @Serial
    private static final long serialVersionUID = 2L;

    @Argument(alias = "rl", description = "RL algorithm: uniform or ucb (default: ucb)")
    protected String rlAlgorithm = "ucb";

    @Argument(alias = "ucbc", description = "Exploration constant for UCB (default: sqrt(2))")
    protected Double ucbC = Math.sqrt(2);

    @Argument(alias = "ops", description = "Operator set: traditional, llm, all (default: traditional)")
    protected String operatorSet = "traditional";

    @Argument(alias = "rllog", description = "RL-specific log file")
    protected String rlLogFile = "rl_operator_log.csv";

    @Argument(alias = "st", description = "Per-step timeout in seconds (default: 180)")
    protected int stepTimeoutSeconds = 180;

    private OperatorSelector operatorSelector;
    private List<Class<? extends Edit>> operators;
    private PrintWriter rlLogWriter;
    private Random rlRng;
    private ExecutorService stepExecutor;

    private int totalSteps = 0;
    private int improvingSteps = 0;

    private List<MethodRuntimeResult> methodResults = new ArrayList<>();

    private static class MethodRuntimeResult {
        String methodName;
        double baselineRuntime;
        double bestRuntime;
        String bestPatch;

        MethodRuntimeResult(String name, double baseline, double best, String patch) {
            this.methodName = name;
            this.baselineRuntime = baseline;
            this.bestRuntime = best;
            this.bestPatch = patch;
        }

        double improvementPercent() {
            if (baselineRuntime == 0) return 0;
            return 100.0 * (baselineRuntime - bestRuntime) / baselineRuntime;
        }
    }

    public RLLocalSearchRuntime(String[] args) {
        super(args);
        Args.parseOrExit(this, args);
        initializeRL();
    }

    public RLLocalSearchRuntime(File projectDir, File methodFile) {
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
            rlLogWriter.println("MethodID,Step,Operator,Success,ParentRuntime(ms),ChildRuntime(ms),Reward");
        } catch (IOException e) {
            Logger.error("Failed to create RL log file: " + e.getMessage());
        }

        this.stepExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r);
            t.setDaemon(true);
            return t;
        });

        Logger.info("=== RLLocalSearchRuntime ===");
        Logger.info("RL Algorithm: " + rlAlgorithm);
        Logger.info("UCB c: " + ucbC);
        Logger.info("Operators: " + operators.size() + " (" + operatorSet + ")");
        Logger.info("Per-step timeout: " + stepTimeoutSeconds + "s");
        Logger.info("============================");
    }

    @Override
    protected void writeNewHeader() {
        String[] entry = { "MethodName"
                , "Iteration"
                , "EvaluationNumber"
                , "Patch"
                , "Compiled"
                , "AllTestsPassed"
                , "TotalExecutionTime(ms)"
                , "Runtime(ms)"
                , "RuntimeImprovement(ms)"
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
        RLLocalSearchRuntime search = new RLLocalSearchRuntime(args);
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
            return (double) (results.totalExecutionTime() / 1000000);
        }
        return Double.MAX_VALUE;
    }

    @Override
    protected boolean fitnessThreshold(UnitTestResultSet results, double orig) {
        return results.allTestsSuccessful();
    }

    @Override
    protected double compareFitness(double newFitness, double oldFitness) {
        return oldFitness - newFitness; // Lower runtime is better
    }

    @Override
    protected void search(TargetMethod method, Patch origPatch) {
        Logger.info("Running RL-guided local search for runtime with " + rlAlgorithm.toUpperCase());

        String className = method.getClassName();
        String methodName = method.toString();
        List<UnitTest> tests = method.getGinTests();
        Integer methodID = method.getMethodID();

        UnitTestResultSet results = initFitness(className, tests, origPatch);
        double origFitness = fitness(results);
        super.writePatch(-1, 0, results, methodName, origFitness, 0);

        Logger.info("Original runtime: " + origFitness + " ms");

        double bestFitness = origFitness;
        Patch bestPatch = origPatch;

        if (operatorSelector instanceof AbstractBanditSelector bandit) {
            bandit.reset();
        }

        for (int step = 1; step < super.indNumber; step++) {
            totalSteps++;

            Class<? extends Edit> selectedOperator = operatorSelector.select();
            Patch neighbour;
            try {
                neighbour = createNeighbour(bestPatch, selectedOperator);
            } catch (Exception e) {
                Logger.warn("createNeighbour failed at step " + step + " (operator: "
                        + selectedOperator.getSimpleName() + "): " + e.getMessage());
                operatorSelector.updateQuality(selectedOperator, (long) bestFitness, null, false);
                logRLStep(methodID, step, selectedOperator, false, bestFitness, -1, 0.0);
                continue;
            }

            final Patch neighbourFinal = neighbour;
            Future<UnitTestResultSet> future = stepExecutor.submit(() -> {
                try {
                    return testPatch(className, tests, neighbourFinal, null);
                } catch (Exception e) {
                    Logger.warn("testPatch threw in executor thread: " + e.getMessage());
                    return null;
                }
            });

            UnitTestResultSet stepResults;
            try {
                stepResults = future.get(stepTimeoutSeconds, TimeUnit.SECONDS);
            } catch (TimeoutException e) {
                future.cancel(true);
                killChildProcesses();
                recycleExecutor();
                Logger.warn(String.format("Step %d timed out after %ds — skipping (operator: %s)",
                        step, stepTimeoutSeconds, selectedOperator.getSimpleName()));
                operatorSelector.updateQuality(selectedOperator, (long) bestFitness, null, false);
                logRLStep(methodID, step, selectedOperator, false, bestFitness, -1, 0.0);
                continue;
            } catch (InterruptedException | ExecutionException e) {
                future.cancel(true);
                killChildProcesses();
                recycleExecutor();
                Logger.warn("Step " + step + " threw exception: " + e.getMessage());
                operatorSelector.updateQuality(selectedOperator, (long) bestFitness, null, false);
                logRLStep(methodID, step, selectedOperator, false, bestFitness, -1, 0.0);
                continue;
            }

            if (stepResults == null) {
                operatorSelector.updateQuality(selectedOperator, (long) bestFitness, null, false);
                logRLStep(methodID, step, selectedOperator, false, bestFitness, -1, 0.0);
                continue;
            }
            results = stepResults;
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
                Logger.info(String.format("Step %d: NEW BEST - %.2f ms (%.1f%% improvement) using %s",
                        step, bestFitness, pctImprovement, selectedOperator.getSimpleName()));
            } else {
                Logger.debug(String.format("Step %d: %s - %s",
                        step, selectedOperator.getSimpleName(),
                        success ? "no improvement" : "failed"));
            }
        }

        double finalImprovement = 100.0 * (origFitness - bestFitness) / origFitness;
        Logger.info(String.format("Method %s: Original=%.2f ms, Best=%.2f ms (%.1f%% improvement)",
                methodName, origFitness, bestFitness, finalImprovement));

        methodResults.add(new MethodRuntimeResult(
                methodName, origFitness, bestFitness, bestPatch.toString()));
    }

    // Thread.interrupt() cannot break through subprocess I/O blocking, so we use
    // ProcessHandle to forcibly kill stuck child JVMs on timeout.
    private void killChildProcesses() {
        ProcessHandle.current().children().forEach(child -> {
            long pid = child.pid();
            child.descendants().forEach(ProcessHandle::destroyForcibly);
            child.destroyForcibly();
            Logger.info("Killed stuck child process tree: PID " + pid);
        });
    }

    // After a timeout the executor thread is stuck on I/O; replace it so the search continues.
    private void recycleExecutor() {
        stepExecutor.shutdownNow();
        stepExecutor = Executors.newSingleThreadExecutor(r -> {
            Thread t = new Thread(r);
            t.setDaemon(true);
            return t;
        });
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
            rlLogWriter.printf("%d,%d,%s,%b,%.2f,%.2f,%.4f%n",
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

        String summaryFile = rlLogFile.replace(".csv", "_runtime_summary.csv");
        writeSummaryCSV(summaryFile);
        Logger.info("Runtime summary saved to: " + summaryFile);
        Logger.info("=".repeat(60));

        if (rlLogWriter != null) {
            rlLogWriter.close();
        }

        stepExecutor.shutdownNow();
    }

    private void writeSummaryCSV(String filename) {
        try (PrintWriter writer = new PrintWriter(new FileWriter(filename))) {
            writer.println("MethodName,BaselineRuntime(ms),BestRuntime(ms),RuntimeReduction(ms),ImprovementPercent,BestPatch");

            for (MethodRuntimeResult result : methodResults) {
                double reduction = result.baselineRuntime - result.bestRuntime;
                String patchStr = result.bestPatch.replace(",", ";").replace("\"", "'");
                writer.printf("\"%s\",%.2f,%.2f,%.2f,%.2f,\"%s\"%n",
                        result.methodName,
                        result.baselineRuntime,
                        result.bestRuntime,
                        reduction,
                        result.improvementPercent(),
                        patchStr);
            }

            double totalBaseline = methodResults.stream().mapToDouble(r -> r.baselineRuntime).sum();
            double totalBest = methodResults.stream().mapToDouble(r -> r.bestRuntime).sum();
            double totalReduction = totalBaseline - totalBest;
            double totalPercent = totalBaseline > 0 ? 100.0 * totalReduction / totalBaseline : 0;
            writer.printf("\"TOTAL\",%.2f,%.2f,%.2f,%.2f,\"%s\"%n",
                    totalBaseline, totalBest, totalReduction, totalPercent, "");

        } catch (IOException e) {
            Logger.error("Failed to write summary CSV: " + e.getMessage());
        }
    }

    // Required by GP but unused in local search
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
