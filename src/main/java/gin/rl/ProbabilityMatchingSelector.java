package gin.rl;

import gin.edit.Edit;
import org.pmw.tinylog.Logger;

import java.io.Serial;
import java.util.*;

/**
 * Probability Matching operator selector.
 *
 * Selection probabilities: p(a) = p_min + (1 - n * p_min) * Q(a) / Σ Q(b)
 * Falls back to uniform when all Q-values are 0
 */
public class ProbabilityMatchingSelector extends AbstractBanditSelector {

    @Serial
    private static final long serialVersionUID = 1L;

    private final double pMin;
    private double[] probabilities;
    private final List<double[]> probabilitiesLog;

    public ProbabilityMatchingSelector(List<Class<? extends Edit>> operators, double pMin, Random rng) {
        super(operators, rng);

        if (pMin <= 0) {
            throw new IllegalArgumentException("pMin must be positive, got: " + pMin);
        }
        if (operators.size() * pMin >= 1.0) {
            throw new IllegalArgumentException(
                "pMin too large: " + operators.size() + " * " + pMin + " = " +
                (operators.size() * pMin) + " >= 1.0");
        }

        this.pMin = pMin;

        int n = operators.size();
        this.probabilities = new double[n];
        Arrays.fill(probabilities, 1.0 / n);

        this.probabilitiesLog = new ArrayList<>();
        probabilitiesLog.add(probabilities.clone());

        Logger.info("Created ProbabilityMatchingSelector with pMin=" + pMin);
    }

    private void updateProbabilities() {
        int n = operators.size();

        double totalQ = 0;
        for (Class<? extends Edit> op : operators) {
            totalQ += averageQualities.get(op);
        }

        if (totalQ <= 0) {
            Arrays.fill(probabilities, 1.0 / n);
        } else {
            double remainingProbability = 1.0 - n * pMin;
            for (int i = 0; i < n; i++) {
                Class<? extends Edit> op = operators.get(i);
                double q = averageQualities.get(op);
                probabilities[i] = pMin + remainingProbability * (q / totalQ);
            }
        }

        double sum = Arrays.stream(probabilities).sum();
        if (sum > 0) {
            for (int i = 0; i < n; i++) {
                probabilities[i] /= sum;
            }
        }
    }

    @Override
    public Class<? extends Edit> select() {
        preSelect();

        double r = rng.nextDouble();
        double cumulative = 0;

        Class<? extends Edit> selected = null;
        for (int i = 0; i < operators.size(); i++) {
            cumulative += probabilities[i];
            if (r <= cumulative) {
                selected = operators.get(i);
                break;
            }
        }

        if (selected == null) {
            selected = operators.get(operators.size() - 1);
        }

        Logger.debug("ProbabilityMatching: selected " + selected.getSimpleName() +
                " (p=" + String.format("%.4f", probabilities[operators.indexOf(selected)]) + ")");

        postSelect(selected);
        return selected;
    }

    @Override
    public void updateQuality(Class<? extends Edit> operator, Long parentFitness,
                              Long childFitness, boolean success) {
        super.updateQuality(operator, parentFitness, childFitness, success);
        updateProbabilities();
        probabilitiesLog.add(probabilities.clone());
        Logger.debug("ProbabilityMatching: updated probabilities");
    }

    public double[] getProbabilities() {
        return probabilities.clone();
    }

    public Map<Class<? extends Edit>, Double> getProbabilityMap() {
        Map<Class<? extends Edit>, Double> probMap = new HashMap<>();
        for (int i = 0; i < operators.size(); i++) {
            probMap.put(operators.get(i), probabilities[i]);
        }
        return probMap;
    }

    public double getPMin() {
        return pMin;
    }

    public List<double[]> getProbabilitiesLog() {
        return Collections.unmodifiableList(probabilitiesLog);
    }

    @Override
    public void reset() {
        super.reset();

        int n = operators.size();
        Arrays.fill(probabilities, 1.0 / n);

        probabilitiesLog.clear();
        probabilitiesLog.add(probabilities.clone());
    }

    @Override
    public String toString() {
        return "ProbabilityMatchingSelector{pMin=" + pMin +
                ", operators=" + operators.size() + "}";
    }
}
