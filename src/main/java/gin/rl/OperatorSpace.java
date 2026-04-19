package gin.rl;

import gin.edit.Edit;
import gin.edit.statement.*;
import gin.edit.matched.*;
import gin.edit.modifynode.*;
import gin.edit.llm.*;

import java.util.*;

/**
 * Defines the space of available mutation operators for RL-based selection.
 */
public class OperatorSpace {

    public static List<Class<? extends Edit>> getStatementOperators() {
        return Arrays.asList(
            DeleteStatement.class,
            CopyStatement.class,
            ReplaceStatement.class,
            SwapStatement.class,
            MoveStatement.class
        );
    }

    public static List<Class<? extends Edit>> getMatchedOperators() {
        return Arrays.asList(
            MatchedDeleteStatement.class,
            MatchedCopyStatement.class,
            MatchedReplaceStatement.class,
            MatchedSwapStatement.class
        );
    }

    public static List<Class<? extends Edit>> getModifyNodeOperators() {
        return Arrays.asList(
            BinaryOperatorReplacement.class,
            UnaryOperatorReplacement.class
        );
    }

    public static List<Class<? extends Edit>> getTraditionalOperators() {
        List<Class<? extends Edit>> all = new ArrayList<>();
        all.addAll(getStatementOperators());
        all.addAll(getMatchedOperators());
        all.addAll(getModifyNodeOperators());
        return all;
    }

    public static List<Class<? extends Edit>> getLLMOperators() {
        return Arrays.asList(
            LLMMaskedStatement.class,
            LLMReplaceStatement.class
        );
    }

    public static List<Class<? extends Edit>> getAllOperators() {
        List<Class<? extends Edit>> all = new ArrayList<>();
        all.addAll(getTraditionalOperators());
        all.addAll(getLLMOperators());
        return all;
    }

    public static List<Class<? extends Edit>> getOperatorsByCategory(String category) {
        return switch (category.toLowerCase()) {
            case "statement" -> getStatementOperators();
            case "matched" -> getMatchedOperators();
            case "modifynode", "modify_node" -> getModifyNodeOperators();
            case "traditional" -> getTraditionalOperators();
            case "llm" -> getLLMOperators();
            case "all" -> getAllOperators();
            default -> throw new IllegalArgumentException("Unknown operator category: " + category);
        };
    }

    public static boolean isLLMOperator(Class<? extends Edit> operator) {
        return operator.getPackage().getName().contains("llm");
    }

    public static String getOperatorName(Class<? extends Edit> operator) {
        return operator.getSimpleName();
    }

    public static String getOperatorCategory(Class<? extends Edit> operator) {
        if (isLLMOperator(operator)) {
            return "llm";
        } else if (getStatementOperators().contains(operator)) {
            return "statement";
        } else if (getMatchedOperators().contains(operator)) {
            return "matched";
        } else if (getModifyNodeOperators().contains(operator)) {
            return "modifynode";
        } else {
            return "unknown";
        }
    }

    public static void printOperatorSummary() {
        System.out.println("=== Available Operators ===\n");

        System.out.println("Statement Operators (" + getStatementOperators().size() + "):");
        for (Class<? extends Edit> op : getStatementOperators()) {
            System.out.println("  - " + op.getSimpleName());
        }

        System.out.println("\nMatched Operators (" + getMatchedOperators().size() + "):");
        for (Class<? extends Edit> op : getMatchedOperators()) {
            System.out.println("  - " + op.getSimpleName());
        }

        System.out.println("\nNode Modification Operators (" + getModifyNodeOperators().size() + "):");
        for (Class<? extends Edit> op : getModifyNodeOperators()) {
            System.out.println("  - " + op.getSimpleName());
        }

        System.out.println("\nLLM Operators (" + getLLMOperators().size() + "):");
        for (Class<? extends Edit> op : getLLMOperators()) {
            System.out.println("  - " + op.getSimpleName());
        }

        System.out.println("\nTotal: " + getAllOperators().size() + " operators");
    }

    //prevent instantiation
    private OperatorSpace() {}
}
