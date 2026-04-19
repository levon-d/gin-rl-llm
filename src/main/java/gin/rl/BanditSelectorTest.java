package gin.rl;

import gin.edit.Edit;
import gin.edit.statement.*;
import gin.edit.matched.*;
import gin.edit.modifynode.*;

import java.util.*;

/**
 * Test harness for bandit selector implementations.
 *
 * Run with: java -cp gin.jar gin.rl.BanditSelectorTest
 */
public class BanditSelectorTest {

    // Simulated "true" qualities, unknown to the algorithms
    private static final Map<Class<? extends Edit>, Double> TRUE_QUALITIES = new HashMap<>();

    static {
        TRUE_QUALITIES.put(DeleteStatement.class, 0.3);
        TRUE_QUALITIES.put(CopyStatement.class, 0.5);
        TRUE_QUALITIES.put(ReplaceStatement.class, 0.7);
        TRUE_QUALITIES.put(SwapStatement.class, 0.4);
        TRUE_QUALITIES.put(MoveStatement.class, 0.35);
        TRUE_QUALITIES.put(BinaryOperatorReplacement.class, 0.6);
        TRUE_QUALITIES.put(UnaryOperatorReplacement.class, 0.45);
        TRUE_QUALITIES.put(MatchedDeleteStatement.class, 0.35);
        TRUE_QUALITIES.put(MatchedCopyStatement.class, 0.55);
        TRUE_QUALITIES.put(MatchedReplaceStatement.class, 0.75);
        TRUE_QUALITIES.put(MatchedSwapStatement.class, 0.5);
    }

    private static final List<Class<? extends Edit>> OPERATORS = new ArrayList<>(TRUE_QUALITIES.keySet());

    private final Random simulationRng;

    public BanditSelectorTest(long seed) {
        this.simulationRng = new Random(seed);
    }

    private SimulatedResult simulateOperator(Class<? extends Edit> operator) {
        double trueQuality = TRUE_QUALITIES.get(operator);

        boolean success = simulationRng.nextDouble() < (0.3 + 0.6 * trueQuality);

        if (!success) {
            return new SimulatedResult(1000L, null, false);
        }

        long parentFitness = 1000L;
        double noiseMultiplier = 0.8 + 0.4 * simulationRng.nextDouble();
        double expectedReward = trueQuality * noiseMultiplier;
        long childFitness = (long) (parentFitness / Math.max(0.1, expectedReward));

        return new SimulatedResult(parentFitness, childFitness, true);
    }

    record SimulatedResult(Long parentFitness, Long childFitness, boolean success) {}

    public TestResult runTest(OperatorSelector selector, int numSteps) {
        double totalReward = 0;
        int successCount = 0;
        List<Double> rewards = new ArrayList<>();
        List<Class<? extends Edit>> selections = new ArrayList<>();

        for (int step = 0; step < numSteps; step++) {
            Class<? extends Edit> selected = selector.select();
            selections.add(selected);

            SimulatedResult result = simulateOperator(selected);
            selector.updateQuality(selected, result.parentFitness, result.childFitness, result.success);

            double reward = result.success && result.childFitness != null
                ? (double) result.parentFitness / result.childFitness
                : 0.0;
            rewards.add(reward);
            totalReward += reward;
            if (result.success) successCount++;
        }

        return new TestResult(selector, numSteps, totalReward, successCount, rewards, selections);
    }

    record TestResult(
        OperatorSelector selector,
        int numSteps,
        double totalReward,
        int successCount,
        List<Double> rewards,
        List<Class<? extends Edit>> selections
    ) {
        double averageReward() { return totalReward / numSteps; }
        double successRate() { return (double) successCount / numSteps; }

        double cumulativeRegret() {
            double bestQuality = TRUE_QUALITIES.values().stream().mapToDouble(d -> d).max().orElse(0);
            double optimalReward = numSteps * bestQuality;
            return optimalReward - totalReward;
        }
    }

    public void printResults(TestResult result) {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("Selector: " + result.selector.getClass().getSimpleName());
        System.out.println("=".repeat(70));

        System.out.printf("Steps: %d%n", result.numSteps);
        System.out.printf("Total Reward: %.2f%n", result.totalReward);
        System.out.printf("Average Reward: %.4f%n", result.averageReward());
        System.out.printf("Success Rate: %.1f%%%n", result.successRate() * 100);
        System.out.printf("Cumulative Regret: %.2f%n", result.cumulativeRegret());

        if (result.selector instanceof AbstractBanditSelector bandit) {
            System.out.println("\nLearned Q-values vs True Qualities:");
            System.out.printf("%-30s %10s %10s %8s%n", "Operator", "Learned Q", "True Q", "Count");
            System.out.println("-".repeat(62));

            Map<Class<? extends Edit>, Double> learnedQ = bandit.getAverageQualities();
            Map<Class<? extends Edit>, Integer> counts = bandit.getActionCounts();

            List<Class<? extends Edit>> sorted = new ArrayList<>(OPERATORS);
            sorted.sort((a, b) -> Double.compare(learnedQ.get(b), learnedQ.get(a)));

            for (Class<? extends Edit> op : sorted) {
                System.out.printf("%-30s %10.4f %10.4f %8d%n",
                    op.getSimpleName(),
                    learnedQ.get(op),
                    TRUE_QUALITIES.get(op),
                    counts.get(op));
            }
        }

        System.out.println("\nSelection Distribution:");
        Map<Class<? extends Edit>, Integer> selectionCounts = new HashMap<>();
        for (Class<? extends Edit> op : OPERATORS) {
            selectionCounts.put(op, 0);
        }
        for (Class<? extends Edit> sel : result.selections) {
            selectionCounts.merge(sel, 1, Integer::sum);
        }

        List<Map.Entry<Class<? extends Edit>, Integer>> sortedSelections = new ArrayList<>(selectionCounts.entrySet());
        sortedSelections.sort((a, b) -> Integer.compare(b.getValue(), a.getValue()));

        for (Map.Entry<Class<? extends Edit>, Integer> entry : sortedSelections) {
            int count = entry.getValue();
            double pct = 100.0 * count / result.numSteps;
            String bar = "#".repeat((int)(pct / 2));
            System.out.printf("%-30s %5d (%5.1f%%) %s%n",
                entry.getKey().getSimpleName(), count, pct, bar);
        }

        System.out.println("\nReward over time (moving average, window=50):");
        printRewardCurve(result.rewards, 50);
    }

    private void printRewardCurve(List<Double> rewards, int windowSize) {
        int numPoints = 10;
        int stepSize = rewards.size() / numPoints;

        System.out.printf("%-10s %s%n", "Step", "Avg Reward");
        for (int i = 0; i < numPoints; i++) {
            int start = i * stepSize;
            int end = Math.min(start + windowSize, rewards.size());
            double avg = rewards.subList(start, end).stream().mapToDouble(d -> d).average().orElse(0);
            String bar = "*".repeat((int)(avg * 20));
            System.out.printf("%-10d %.4f %s%n", start, avg, bar);
        }
    }

    public void compareSelectors(int numSteps, int numTrials) {
        System.out.println("\n" + "=".repeat(70));
        System.out.println("COMPARISON: " + numTrials + " trials x " + numSteps + " steps each");
        System.out.println("Best possible operator: MatchedReplaceStatement (true Q = 0.75)");
        System.out.println("=".repeat(70));

        Map<String, List<TestResult>> allResults = new LinkedHashMap<>();

        String[] selectorNames = {"Uniform", "EpsilonGreedy(0.1)", "EpsilonGreedy(0.2)",
                                   "UCB(sqrt2)", "PolicyGradient(0.1)", "ProbabilityMatching(0.05)"};

        for (String name : selectorNames) allResults.put(name, new ArrayList<>());

        for (int trial = 0; trial < numTrials; trial++) {
            Random trialRng = new Random(trial * 12345L);

            allResults.get("Uniform").add(
                runTest(new UniformSelector(OPERATORS, new Random(trialRng.nextLong())), numSteps));
            allResults.get("EpsilonGreedy(0.1)").add(
                runTest(new EpsilonGreedySelector(OPERATORS, 0.1, new Random(trialRng.nextLong())), numSteps));
            allResults.get("EpsilonGreedy(0.2)").add(
                runTest(new EpsilonGreedySelector(OPERATORS, 0.2, new Random(trialRng.nextLong())), numSteps));
            allResults.get("UCB(sqrt2)").add(
                runTest(new UCBSelector(OPERATORS, Math.sqrt(2), new Random(trialRng.nextLong())), numSteps));
            allResults.get("PolicyGradient(0.1)").add(
                runTest(new PolicyGradientSelector(OPERATORS, 0.1, new Random(trialRng.nextLong())), numSteps));
            allResults.get("ProbabilityMatching(0.05)").add(
                runTest(new ProbabilityMatchingSelector(OPERATORS, 0.05, new Random(trialRng.nextLong())), numSteps));
        }

        System.out.printf("%n%-25s %12s %12s %12s %12s%n",
            "Selector", "Avg Reward", "Std Dev", "Success%", "Regret");
        System.out.println("-".repeat(75));

        for (Map.Entry<String, List<TestResult>> entry : allResults.entrySet()) {
            List<TestResult> results = entry.getValue();

            double avgReward = results.stream().mapToDouble(TestResult::averageReward).average().orElse(0);
            double stdReward = Math.sqrt(results.stream()
                .mapToDouble(r -> Math.pow(r.averageReward() - avgReward, 2))
                .average().orElse(0));
            double avgSuccess = results.stream().mapToDouble(TestResult::successRate).average().orElse(0);
            double avgRegret = results.stream().mapToDouble(TestResult::cumulativeRegret).average().orElse(0);

            System.out.printf("%-25s %12.4f %12.4f %11.1f%% %12.1f%n",
                entry.getKey(), avgReward, stdReward, avgSuccess * 100, avgRegret);
        }
    }

    public static void main(String[] args) {
        System.out.println("Bandit Selector Test Harness");
        System.out.println("============================\n");

        System.out.println("True operator qualities (simulated):");
        TRUE_QUALITIES.entrySet().stream()
            .sorted((a, b) -> Double.compare(b.getValue(), a.getValue()))
            .forEach(e -> System.out.printf("  %-30s %.2f%n", e.getKey().getSimpleName(), e.getValue()));

        BanditSelectorTest tester = new BanditSelectorTest(42);
        int numSteps = 500;

        System.out.println("\n\n>>> DETAILED INDIVIDUAL TESTS (" + numSteps + " steps) <<<");

        tester.printResults(tester.runTest(
            new UniformSelector(OPERATORS, new Random(123)), numSteps));

        tester.printResults(tester.runTest(
            new EpsilonGreedySelector(OPERATORS, 0.2, new Random(123)), numSteps));

        tester.printResults(tester.runTest(
            new UCBSelector(OPERATORS, Math.sqrt(2), new Random(123)), numSteps));

        tester.printResults(tester.runTest(
            new PolicyGradientSelector(OPERATORS, 0.1, new Random(123)), numSteps));

        tester.printResults(tester.runTest(
            new ProbabilityMatchingSelector(OPERATORS, 0.05, new Random(123)), numSteps));

        System.out.println("\n\n>>> STATISTICAL COMPARISON <<<");
        tester.compareSelectors(500, 10);

        System.out.println("\n\nTest complete!");
    }
}
