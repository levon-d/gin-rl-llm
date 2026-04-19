package gin.rl;

import com.sampullara.cli.Args;
import com.sampullara.cli.Argument;
import gin.Patch;
import gin.SourceFile;
import gin.edit.Edit;
import gin.edit.llm.LLMConfig;
import gin.edit.llm.LLMConfig.PromptType;
import gin.test.InternalTestRunner;
import gin.test.UnitTestResult;
import gin.test.UnitTestResultSet;
import org.apache.commons.io.FilenameUtils;
import org.apache.commons.rng.simple.JDKRandomBridge;
import org.apache.commons.rng.simple.RandomSource;
import org.pmw.tinylog.Logger;

import java.io.File;
import java.io.IOException;
import java.io.Serial;
import java.io.Serializable;
import java.util.*;

/**
 * RL-based Local Search for Genetic Improvement.
 *
 * Usage: java -cp gin.jar gin.rl.RLLocalSearch -f MyClass.java -m "myMethod()" -rl epsilon_greedy
 */
public class RLLocalSearch implements Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    private static final int WARMUP_REPS = 10;

    @Argument(alias = "f", description = "Required: Source filename", required = true)
    protected File filename = null;

    @Argument(alias = "m", description = "Required: Method signature", required = true)
    protected String methodSignature = "";

    @Argument(alias = "d", description = "Top directory")
    protected File packageDir;

    @Argument(alias = "c", description = "Class name")
    protected String className;

    @Argument(alias = "cp", description = "Classpath")
    protected String classPath;

    @Argument(alias = "t", description = "Test class name")
    protected String testClassName;

    @Argument(alias = "s", description = "Random seed")
    protected Integer seed = 123;

    @Argument(alias = "n", description = "Number of steps")
    protected Integer numSteps = 100;

    @Argument(alias = "ff", description = "Fail fast on test failures")
    protected Boolean failFast = false;

    @Argument(alias = "rl", description = "RL algorithm: uniform, epsilon_greedy, ucb, policy_gradient, probability_matching")
    protected String rlAlgorithm = "epsilon_greedy";

    @Argument(alias = "eps", description = "Epsilon for epsilon-greedy (exploration rate)")
    protected Double epsilon = 0.2;

    @Argument(alias = "ucbc", description = "Exploration constant c for UCB")
    protected Double ucbC = Math.sqrt(2);

    @Argument(alias = "alpha", description = "Learning rate for policy gradient")
    protected Double alpha = 0.1;

    @Argument(alias = "pmin", description = "Minimum probability for probability matching")
    protected Double pMin = 0.05;

    @Argument(alias = "ft", description = "Fitness type: runtime or memory")
    protected String fitnessType = "memory";

    @Argument(alias = "ops", description = "Operator set: traditional, llm, all")
    protected String operatorSet = "all";

    @Argument(alias = "oaik", description = "OpenAI API key")
    protected String openAIKey = "demo";

    @Argument(alias = "oain", description = "OpenAI model name")
    protected String openAIName = "gpt-3.5-turbo";

    @Argument(alias = "pt", description = "LLM prompt type")
    protected PromptType llmPromptType = PromptType.MEDIUM;

    @Argument(alias = "mt", description = "Model type: OpenAI or ollama model name")
    protected String modelType = "OpenAI";

    @Argument(alias = "o", description = "Output directory for logs")
    protected String outputDir = "rl_results";

    @Argument(alias = "expid", description = "Experiment ID (auto-generated if not specified)")
    protected String experimentId = null;

    protected SourceFile sourceFile;
    protected Random rng;
    protected InternalTestRunner testRunner;
    protected OperatorSelector operatorSelector;
    protected List<Class<? extends Edit>> operators;
    protected ExperimentLogger logger;

    public RLLocalSearch(String[] args) {
        Args.parseOrExit(this, args);
        initialize();
    }

    private void initialize() {
        this.rng = new JDKRandomBridge(RandomSource.MT, Long.valueOf(seed));

        if (this.packageDir == null) {
            this.packageDir = (this.filename.getParentFile() != null)
                ? this.filename.getParentFile().getAbsoluteFile()
                : new File(System.getProperty("user.dir"));
        }
        if (this.classPath == null) {
            this.classPath = this.packageDir.getAbsolutePath();
        }
        if (this.className == null) {
            this.className = FilenameUtils.removeExtension(this.filename.getName());
        }
        if (this.testClassName == null) {
            this.testClassName = this.className + "Test";
        }

        this.operators = OperatorSpace.getOperatorsByCategory(operatorSet);

        List<Edit.EditType> editTypes = new ArrayList<>();
        editTypes.add(Edit.EditType.STATEMENT);
        editTypes.add(Edit.EditType.MATCHED_STATEMENT);
        editTypes.add(Edit.EditType.MODIFY_STATEMENT);
        this.sourceFile = SourceFile.makeSourceFileForEditTypes(
            Edit.getEditClassesOfTypes(editTypes),
            this.filename.toString(),
            Collections.singletonList(this.methodSignature)
        );

        this.testRunner = new InternalTestRunner(className, classPath, testClassName, failFast);

        LLMConfig.openAIKey = openAIKey;
        LLMConfig.openAIModelName = openAIName;
        LLMConfig.defaultPromptType = llmPromptType;
        LLMConfig.modelType = modelType;

        this.operatorSelector = createSelector();

        this.logger = new ExperimentLogger(
            experimentId != null ? experimentId : generateExperimentId(),
            outputDir
        );
        this.logger.setFitnessUnit(getFitnessUnit());

        logConfiguration();

        Logger.info("RLLocalSearch initialized");
        Logger.info("  Algorithm: " + rlAlgorithm);
        Logger.info("  Fitness: " + fitnessType);
        Logger.info("  Operators: " + operators.size() + " (" + operatorSet + ")");
        Logger.info("  Steps: " + numSteps);
    }

    private long getFitness(UnitTestResultSet results) {
        return fitnessType.equalsIgnoreCase("memory")
            ? results.totalMemoryUsage()
            : results.totalExecutionTime();
    }

    private String getFitnessUnit() {
        return fitnessType.equalsIgnoreCase("memory") ? "bytes" : "ns";
    }

    private String generateExperimentId() {
        return String.format("%s_%s_%d", rlAlgorithm, operatorSet, seed);
    }

    private OperatorSelector createSelector() {
        return switch (rlAlgorithm.toLowerCase()) {
            case "uniform", "random" -> new UniformSelector(operators, rng);
            case "epsilon_greedy", "epsilon-greedy", "egreedy" ->
                new EpsilonGreedySelector(operators, epsilon, rng);
            case "ucb", "ucb1" -> new UCBSelector(operators, ucbC, rng);
            case "policy_gradient", "policy-gradient", "pg", "reinforce" ->
                new PolicyGradientSelector(operators, alpha, rng);
            case "probability_matching", "probability-matching", "pm" ->
                new ProbabilityMatchingSelector(operators, pMin, rng);
            default -> throw new IllegalArgumentException("Unknown RL algorithm: " + rlAlgorithm);
        };
    }

    private void logConfiguration() {
        logger.setConfiguration("source_file", filename.toString());
        logger.setConfiguration("method_signature", methodSignature);
        logger.setConfiguration("class_name", className);
        logger.setConfiguration("seed", String.valueOf(seed));
        logger.setConfiguration("num_steps", String.valueOf(numSteps));
        logger.setConfiguration("rl_algorithm", rlAlgorithm);
        logger.setConfiguration("operator_set", operatorSet);
        logger.setConfiguration("num_operators", String.valueOf(operators.size()));
        logger.setConfiguration("fitness_type", fitnessType);

        switch (rlAlgorithm.toLowerCase()) {
            case "epsilon_greedy", "epsilon-greedy", "egreedy" ->
                logger.setConfiguration("epsilon", String.valueOf(epsilon));
            case "ucb", "ucb1" ->
                logger.setConfiguration("ucb_c", String.valueOf(ucbC));
            case "policy_gradient", "policy-gradient", "pg", "reinforce" ->
                logger.setConfiguration("alpha", String.valueOf(alpha));
            case "probability_matching", "probability-matching", "pm" ->
                logger.setConfiguration("p_min", String.valueOf(pMin));
        }

        if (operatorSet.equals("llm") || operatorSet.equals("all")) {
            logger.setConfiguration("llm_model", modelType.equals("OpenAI") ? openAIName : modelType);
            logger.setConfiguration("llm_prompt_type", llmPromptType.toString());
        }
    }

    private long warmup() {
        Logger.info("Running warmup...");

        Patch emptyPatch = new Patch(this.sourceFile);
        UnitTestResultSet resultSet = testRunner.runTests(emptyPatch, null, WARMUP_REPS);

        if (!resultSet.allTestsSuccessful()) {
            if (!resultSet.getCleanCompile()) {
                Logger.error("Original code failed to compile");
            } else {
                Logger.error("Original code failed tests:");
                for (UnitTestResult r : resultSet.getResults()) {
                    Logger.error("  " + r);
                }
            }
            System.exit(1);
        }

        long avgFitness = getFitness(resultSet) / WARMUP_REPS;
        Logger.info("Original fitness: " + avgFitness + " " + getFitnessUnit());

        return avgFitness;
    }

    public void search() {
        Logger.info("Starting RL Local Search");
        Logger.info("  File: " + filename);
        Logger.info("  Method: " + methodSignature);

        long originalFitness = warmup();
        logger.setOriginalFitness(originalFitness);

        Patch bestPatch = new Patch(this.sourceFile);
        long bestFitness = originalFitness;

        for (int step = 1; step <= numSteps; step++) {
            long stepStartTime = System.currentTimeMillis();

            Class<? extends Edit> selectedOperator = operatorSelector.select();

            Logger.info(String.format("Step %d/%d: Trying %s",
                step, numSteps, selectedOperator.getSimpleName()));

            Patch neighbour = createNeighbour(bestPatch, selectedOperator);
            UnitTestResultSet results = testRunner.runTests(neighbour, null, 1);

            boolean success = results.getValidPatch()
                           && results.getCleanCompile()
                           && results.allTestsSuccessful();

            Long childFitness = success ? getFitness(results) : null;
            double reward = calculateReward(bestFitness, childFitness, success);

            operatorSelector.updateQuality(selectedOperator, bestFitness, childFitness, success);

            long stepDuration = System.currentTimeMillis() - stepStartTime;
            logger.logStep(step, selectedOperator, success, bestFitness, childFitness,
                          reward, stepDuration, neighbour.toString());

            String msg;
            if (!results.getValidPatch()) {
                msg = "Invalid patch";
            } else if (!results.getCleanCompile()) {
                msg = "Compilation failed";
            } else if (!results.allTestsSuccessful()) {
                msg = "Tests failed";
            } else if (childFitness >= bestFitness) {
                msg = String.format("No improvement (%d %s)", childFitness, getFitnessUnit());
            } else {
                bestPatch = neighbour;
                bestFitness = childFitness;
                msg = String.format("*** NEW BEST: %d %s (%.1f%% improvement) ***",
                    bestFitness, getFitnessUnit(), 100.0 * (originalFitness - bestFitness) / originalFitness);
            }

            Logger.info(String.format("  Result: %s, Reward: %.4f", msg, reward));
        }

        double improvement = 100.0 * (originalFitness - bestFitness) / originalFitness;
        String unit = getFitnessUnit();
        Logger.info("=".repeat(60));
        Logger.info("Search complete!");
        Logger.info(String.format("  Original: %d %s", originalFitness, unit));
        Logger.info(String.format("  Best:     %d %s (%.1f%% improvement)", bestFitness, unit, improvement));
        Logger.info(String.format("  Patch:    %s", bestPatch));
        Logger.info("=".repeat(60));

        logger.printSummary();

        if (operatorSelector instanceof AbstractBanditSelector bandit) {
            bandit.logOperatorSummary();
        }

        try {
            logger.exportAll(operatorSelector);
        } catch (IOException e) {
            Logger.error("Failed to export results: " + e.getMessage());
        }

        if (bestFitness < originalFitness) {
            String outputPath = sourceFile.getRelativePathToWorkingDir() + ".optimised";
            bestPatch.writePatchedSourceToFile(outputPath, null);
            Logger.info("Optimised source written to: " + outputPath);
        }
    }

    private Patch createNeighbour(Patch patch, Class<? extends Edit> operatorClass) {
        Patch neighbour = patch.clone();
        if (neighbour.size() > 0 && rng.nextFloat() > 0.5) {
            neighbour.remove(rng.nextInt(neighbour.size()));
        } else {
            neighbour.addRandomEditOfClass(rng, operatorClass);
        }

        return neighbour;
    }

    private double calculateReward(Long parentFitness, Long childFitness, boolean success) {
        if (!success || childFitness == null || childFitness <= 0) {
            return 0.0;
        }
        return (double) parentFitness / childFitness;
    }

    public static void main(String[] args) {
        RLLocalSearch search = new RLLocalSearch(args);
        search.search();
    }

    public static void printUsage() {
        System.out.println("RL-based Local Search for Genetic Improvement");
        System.out.println();
        System.out.println("Usage: java -cp gin.jar gin.rl.RLLocalSearch [options]");
        System.out.println();
        System.out.println("Required:");
        System.out.println("  -f <file>      Source file to optimize");
        System.out.println("  -m <method>    Method signature (e.g., \"sort(int[])\")");
        System.out.println();
        System.out.println("RL Options:");
        System.out.println("  -rl <algo>     Algorithm: uniform, epsilon_greedy, ucb, policy_gradient, probability_matching");
        System.out.println("  -eps <value>   Epsilon for epsilon-greedy (default: 0.2)");
        System.out.println("  -ucbc <value>  Exploration constant for UCB (default: sqrt(2))");
        System.out.println("  -alpha <value> Learning rate for policy gradient (default: 0.1)");
        System.out.println("  -pmin <value>  Minimum probability for probability matching (default: 0.05)");
        System.out.println();
        System.out.println("Fitness Options:");
        System.out.println("  -ft <type>     Fitness type: runtime or memory (default: memory)");
        System.out.println();
        System.out.println("Operator Options:");
        System.out.println("  -ops <set>     Operators: traditional, llm, all (default: all)");
        System.out.println();
        System.out.println("LLM Options:");
        System.out.println("  -oaik <key>    OpenAI API key");
        System.out.println("  -oain <model>  OpenAI model name (default: gpt-3.5-turbo)");
        System.out.println("  -mt <type>     Model type: OpenAI or ollama model name");
        System.out.println();
        System.out.println("Search Options:");
        System.out.println("  -n <steps>     Number of search steps (default: 100)");
        System.out.println("  -s <seed>      Random seed (default: 123)");
        System.out.println();
        System.out.println("Output:");
        System.out.println("  -o <dir>       Output directory for logs (default: rl_results)");
        System.out.println("  -expid <id>    Experiment ID for log files");
    }
}
