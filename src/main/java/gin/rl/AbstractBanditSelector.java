package gin.rl;

import gin.edit.Edit;
import org.pmw.tinylog.Logger;

import java.io.Serial;
import java.io.Serializable;
import java.util.*;

/**
 * Abstract base class for Multi-Armed Bandit (MAB) based operator selectors.
 *
 * The reward function uses a ratio-based approach:
 * - reward = parentFitness / childFitness
 * - reward > 1 means improvement (child is faster)
 * - reward = 1 means no change
 * - reward < 1 means degradation
 * - reward = 0 for failed mutations
 */
public abstract class AbstractBanditSelector implements OperatorSelector, Serializable {

    @Serial
    private static final long serialVersionUID = 1L;

    protected final List<Class<? extends Edit>> operators;
    protected final Map<Class<? extends Edit>, Double> averageQualities;
    protected final Map<Class<? extends Edit>, Integer> actionCounts;
    protected final Map<Class<? extends Edit>, Integer> successCounts;
    protected final Map<Class<? extends Edit>, Integer> failureCounts;
    protected final Map<Class<? extends Edit>, Double> totalRewards;
    protected Class<? extends Edit> previousOperator;
    protected final Random rng;

    protected final List<Double> rewardLog;
    protected final List<Map<Class<? extends Edit>, Double>> qualityLog;
    protected final List<Map<Class<? extends Edit>, Integer>> actionCountLog;
    protected final List<Class<? extends Edit>> selectionLog;
    protected final List<Boolean> successLog;

    protected int selectCallCount = 0;
    protected int updateCallCount = 0;

    public AbstractBanditSelector(List<Class<? extends Edit>> operators, Random rng) {
        if (operators == null || operators.isEmpty()) {
            throw new IllegalArgumentException("Operators list cannot be null or empty");
        }

        this.operators = new ArrayList<>(operators);
        this.rng = rng;

        this.averageQualities = new HashMap<>();
        this.actionCounts = new HashMap<>();
        this.successCounts = new HashMap<>();
        this.failureCounts = new HashMap<>();
        this.totalRewards = new HashMap<>();

        for (Class<? extends Edit> op : operators) {
            averageQualities.put(op, 0.0);
            actionCounts.put(op, 0);
            successCounts.put(op, 0);
            failureCounts.put(op, 0);
            totalRewards.put(op, 0.0);
        }

        this.rewardLog = new ArrayList<>();
        this.qualityLog = new ArrayList<>();
        this.actionCountLog = new ArrayList<>();
        this.selectionLog = new ArrayList<>();
        this.successLog = new ArrayList<>();

        this.qualityLog.add(new HashMap<>(averageQualities));
        this.actionCountLog.add(new HashMap<>(actionCounts));

        Logger.info("Initialized bandit selector with " + operators.size() + " operators");
        logOperatorSummary();
    }

    protected double calculateReward(Long parentFitness, Long childFitness, boolean success) {
        if (!success || childFitness == null || childFitness <= 0) {
            return 0.0;
        }
        if (parentFitness == null || parentFitness <= 0) {
            Logger.warn("Invalid parent fitness: " + parentFitness);
            return 0.0;
        }
        return (double) parentFitness / childFitness;
    }

    @Override
    public void updateQuality(Class<? extends Edit> operator, Long parentFitness,
                              Long childFitness, boolean success) {
        if (updateCallCount >= selectCallCount) {
            Logger.warn("updateQuality() called without matching select() call");
        }
        updateCallCount++;

        double reward = calculateReward(parentFitness, childFitness, success);

        int count = actionCounts.get(operator) + 1;
        actionCounts.put(operator, count);

        // Incremental mean: Q(a) = Q(a) + (r - Q(a)) / n(a)
        double oldQ = averageQualities.get(operator);
        double newQ = oldQ + (reward - oldQ) / count;
        averageQualities.put(operator, newQ);

        if (success) {
            successCounts.put(operator, successCounts.get(operator) + 1);
        } else {
            failureCounts.put(operator, failureCounts.get(operator) + 1);
        }

        totalRewards.put(operator, totalRewards.get(operator) + reward);

        rewardLog.add(reward);
        qualityLog.add(new HashMap<>(averageQualities));
        actionCountLog.add(new HashMap<>(actionCounts));
        successLog.add(success);

        Logger.debug(String.format("Updated %s: reward=%.4f, newQ=%.4f, count=%d, success=%b",
                operator.getSimpleName(), reward, newQ, count, success));
    }

    protected void preSelect() {
        if (selectCallCount > 0 && updateCallCount < selectCallCount) {
            Logger.warn("select() called without updateQuality() for previous selection");
        }
        selectCallCount++;
    }

    protected void postSelect(Class<? extends Edit> selected) {
        previousOperator = selected;
        selectionLog.add(selected);
        Logger.debug("Selected operator: " + selected.getSimpleName() +
                     " (LLM: " + isLLMOperator(selected) + ")");
    }

    @Override
    public List<Class<? extends Edit>> getOperators() {
        return Collections.unmodifiableList(operators);
    }

    @Override
    public Class<? extends Edit> getPreviousOperator() {
        return previousOperator;
    }

    @Override
    public Map<Class<? extends Edit>, OperatorStats> getOperatorStatistics() {
        Map<Class<? extends Edit>, OperatorStats> stats = new HashMap<>();
        for (Class<? extends Edit> op : operators) {
            stats.put(op, new OperatorStats(
                actionCounts.get(op),
                averageQualities.get(op),
                successCounts.get(op),
                failureCounts.get(op),
                totalRewards.get(op)
            ));
        }
        return stats;
    }

    public List<Double> getRewardLog() {
        return Collections.unmodifiableList(rewardLog);
    }

    public List<Map<Class<? extends Edit>, Double>> getQualityLog() {
        return Collections.unmodifiableList(qualityLog);
    }

    public List<Map<Class<? extends Edit>, Integer>> getActionCountLog() {
        return Collections.unmodifiableList(actionCountLog);
    }

    public List<Class<? extends Edit>> getSelectionLog() {
        return Collections.unmodifiableList(selectionLog);
    }

    public List<Boolean> getSuccessLog() {
        return Collections.unmodifiableList(successLog);
    }

    public Map<Class<? extends Edit>, Double> getAverageQualities() {
        return Collections.unmodifiableMap(averageQualities);
    }

    public Map<Class<? extends Edit>, Integer> getActionCounts() {
        return Collections.unmodifiableMap(actionCounts);
    }

    public int getTotalSelections() {
        return actionCounts.values().stream().mapToInt(Integer::intValue).sum();
    }

    public Class<? extends Edit> getBestOperator() {
        return Collections.max(operators, Comparator.comparingDouble(averageQualities::get));
    }

    public double getCumulativeReward() {
        return rewardLog.stream().mapToDouble(Double::doubleValue).sum();
    }

    public double getAverageReward() {
        if (rewardLog.isEmpty()) {
            return 0.0;
        }
        return getCumulativeReward() / rewardLog.size();
    }

    public void logOperatorSummary() {
        Logger.info("=== Operator Summary ===");
        Logger.info(String.format("%-35s %8s %8s %10s %8s",
                "Operator", "Count", "AvgQ", "SuccRate", "LLM"));
        Logger.info("-".repeat(75));

        for (Class<? extends Edit> op : operators) {
            int count = actionCounts.get(op);
            double avgQ = averageQualities.get(op);
            int successes = successCounts.get(op);
            int failures = failureCounts.get(op);
            double successRate = (count > 0) ? (double) successes / count : 0.0;
            boolean isLLM = isLLMOperator(op);

            Logger.info(String.format("%-35s %8d %8.4f %9.2f%% %8s",
                    op.getSimpleName(), count, avgQ, successRate * 100, isLLM ? "Yes" : "No"));
        }
        Logger.info("=".repeat(75));
    }

    public void reset() {
        for (Class<? extends Edit> op : operators) {
            averageQualities.put(op, 0.0);
            actionCounts.put(op, 0);
            successCounts.put(op, 0);
            failureCounts.put(op, 0);
            totalRewards.put(op, 0.0);
        }

        previousOperator = null;
        selectCallCount = 0;
        updateCallCount = 0;

        rewardLog.clear();
        qualityLog.clear();
        actionCountLog.clear();
        selectionLog.clear();
        successLog.clear();

        qualityLog.add(new HashMap<>(averageQualities));
        actionCountLog.add(new HashMap<>(actionCounts));

        Logger.info("Bandit selector reset");
    }
}
