package gin.rl;

import gin.edit.Edit;
import org.pmw.tinylog.Logger;

import java.io.Serial;
import java.util.*;

/**
 * Upper Confidence Bound (UCB1) operator selector.
 *
 * Selects the operator maximising: UCB(a) = Q(a) + c * sqrt(ln(t) / n(a))
 */
public class UCBSelector extends AbstractBanditSelector {

    @Serial
    private static final long serialVersionUID = 1L;

    private final double c;
    private final Set<Class<? extends Edit>> unselectedOperators;

    public UCBSelector(List<Class<? extends Edit>> operators, double c, Random rng) {
        super(operators, rng);

        if (c < 0) {
            throw new IllegalArgumentException("Exploration constant c must be non-negative, got: " + c);
        }

        this.c = c;
        this.unselectedOperators = new HashSet<>(operators);

        Logger.info("Created UCBSelector with c=" + c);
    }

    public UCBSelector(List<Class<? extends Edit>> operators, Random rng) {
        this(operators, Math.sqrt(2), rng);
    }

    @Override
    public Class<? extends Edit> select() {
        preSelect();

        Class<? extends Edit> selected;

        if (!unselectedOperators.isEmpty()) {
            List<Class<? extends Edit>> unselectedList = new ArrayList<>(unselectedOperators);
            selected = unselectedList.get(rng.nextInt(unselectedList.size()));
            unselectedOperators.remove(selected);

            Logger.debug("UCB: INITIALIZATION - selecting unselected operator (" +
                    unselectedOperators.size() + " remaining)");
        } else {
            int totalSelections = getTotalSelections();

            selected = Collections.max(operators, (a, b) -> {
                double ucbA = computeUCB(a, totalSelections);
                double ucbB = computeUCB(b, totalSelections);
                return Double.compare(ucbA, ucbB);
            });

            Logger.debug("UCB: selected " + selected.getSimpleName() +
                    " (UCB=" + String.format("%.4f", computeUCB(selected, totalSelections)) + ")");
        }

        postSelect(selected);
        return selected;
    }

    //UCB(a) = Q(a) + c * sqrt(ln(t) / n(a))
    private double computeUCB(Class<? extends Edit> operator, int totalSelections) {
        double q = averageQualities.get(operator);
        int n = actionCounts.get(operator);

        if (n == 0) {
            return Double.MAX_VALUE;
        }

        double explorationBonus = c * Math.sqrt(Math.log(totalSelections) / n);
        return q + explorationBonus;
    }

    public Map<Class<? extends Edit>, Double> getUCBValues() {
        int totalSelections = getTotalSelections();
        Map<Class<? extends Edit>, Double> ucbValues = new HashMap<>();
        for (Class<? extends Edit> op : operators) {
            ucbValues.put(op, computeUCB(op, totalSelections));
        }
        return ucbValues;
    }

    public double getC() {
        return c;
    }

    public boolean isInitialized() {
        return unselectedOperators.isEmpty();
    }

    @Override
    public void reset() {
        super.reset();
        unselectedOperators.clear();
        unselectedOperators.addAll(operators);
    }

    @Override
    public String toString() {
        return "UCBSelector{c=" + c + ", operators=" + operators.size() +
                ", initialized=" + isInitialized() + "}";
    }
}
