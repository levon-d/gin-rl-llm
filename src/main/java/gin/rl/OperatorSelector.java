package gin.rl;

import gin.edit.Edit;

import java.util.List;
import java.util.Map;

/**
 * Interface for RL-based operator selection in Genetic Improvement.
 */
public interface OperatorSelector {

    Class<? extends Edit> select();

    void updateQuality(Class<? extends Edit> operator, Long parentFitness,
                       Long childFitness, boolean success);

    List<Class<? extends Edit>> getOperators();

    Class<? extends Edit> getPreviousOperator();

    default boolean isLLMOperator(Class<? extends Edit> operator) {
        return operator.getPackage().getName().contains("llm");
    }

    Map<Class<? extends Edit>, OperatorStats> getOperatorStatistics();

    record OperatorStats(
        int selectionCount,
        double averageQuality,
        int successCount,
        int failureCount,
        double totalReward
    ) {
        public double getSuccessRate() {
            int total = successCount + failureCount;
            return total > 0 ? (double) successCount / total : 0.0;
        }
    }
}
