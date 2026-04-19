package gin.rl;

import gin.edit.Edit;
import org.pmw.tinylog.Logger;

import java.io.Serial;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;
import java.util.Random;

/**
 * Epsilon-Greedy operator selector.
 */
public class EpsilonGreedySelector extends AbstractBanditSelector {

    @Serial
    private static final long serialVersionUID = 1L;

    private final double epsilon;

    public EpsilonGreedySelector(List<Class<? extends Edit>> operators, double epsilon, Random rng) {
        super(operators, rng);

        if (epsilon < 0 || epsilon > 1) {
            throw new IllegalArgumentException("Epsilon must be between 0 and 1, got: " + epsilon);
        }

        this.epsilon = epsilon;
        Logger.info("Created EpsilonGreedySelector with epsilon=" + epsilon);
    }

    @Override
    public Class<? extends Edit> select() {
        preSelect();

        Class<? extends Edit> selected;

        if (rng.nextDouble() < epsilon) {
            selected = operators.get(rng.nextInt(operators.size()));
            Logger.debug("Epsilon-greedy: EXPLORE - random selection");
        } else {
            selected = Collections.max(operators,
                    Comparator.comparingDouble(averageQualities::get));
            Logger.debug("Epsilon-greedy: EXPLOIT - best operator (Q=" +
                    String.format("%.4f", averageQualities.get(selected)) + ")");
        }

        postSelect(selected);
        return selected;
    }

    public double getEpsilon() {
        return epsilon;
    }

    @Override
    public String toString() {
        return "EpsilonGreedySelector{epsilon=" + epsilon + ", operators=" + operators.size() + "}";
    }
}
