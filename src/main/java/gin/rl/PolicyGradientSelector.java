package gin.rl;

import gin.edit.Edit;
import org.pmw.tinylog.Logger;

import java.io.Serial;
import java.util.*;

/**
 * Policy Gradient (REINFORCE-style) operator selector.
 *
 * Maintains softmax preferences H(a); after each step updates via:
 *   H(a) += α * (R - R̄) * (1 - π(a))   if a was selected
 *   H(a) -= α * (R - R̄) * π(a)         otherwise
 */
public class PolicyGradientSelector extends AbstractBanditSelector {

    @Serial
    private static final long serialVersionUID = 1L;

    private final double alpha;
    private final double[] preferences;
    private double[] policy;
    private double averageReward;
    private double totalReward;
    private int rewardCount;

    private final List<double[]> preferencesLog;
    private final List<double[]> policyLog;
    private final List<Double> averageRewardLog;

    public PolicyGradientSelector(List<Class<? extends Edit>> operators, double alpha, Random rng) {
        super(operators, rng);

        if (alpha <= 0) {
            throw new IllegalArgumentException("Learning rate alpha must be positive, got: " + alpha);
        }

        this.alpha = alpha;

        this.preferences = new double[operators.size()];
        Arrays.fill(preferences, 0.0);

        this.policy = computeSoftmax(preferences);

        this.averageReward = 0.0;
        this.totalReward = 0.0;
        this.rewardCount = 0;

        this.preferencesLog = new ArrayList<>();
        this.policyLog = new ArrayList<>();
        this.averageRewardLog = new ArrayList<>();

        preferencesLog.add(preferences.clone());
        policyLog.add(policy.clone());
        averageRewardLog.add(averageReward);

        Logger.info("Created PolicyGradientSelector with alpha=" + alpha);
    }

    // pi(a) = exp(H(a)) / Σ exp(H(b)); uses log-sum-exp for numerical stability
    private double[] computeSoftmax(double[] prefs) {
        int n = prefs.length;
        double[] result = new double[n];

        double maxPref = Arrays.stream(prefs).max().orElse(0);

        double sum = 0;
        for (int i = 0; i < n; i++) {
            result[i] = Math.exp(prefs[i] - maxPref);
            sum += result[i];
        }

        for (int i = 0; i < n; i++) {
            result[i] /= sum;
        }

        return result;
    }

    @Override
    public Class<? extends Edit> select() {
        preSelect();

        double r = rng.nextDouble();
        double cumulative = 0;

        Class<? extends Edit> selected = null;
        for (int i = 0; i < operators.size(); i++) {
            cumulative += policy[i];
            if (r <= cumulative) {
                selected = operators.get(i);
                break;
            }
        }

        if (selected == null) {
            selected = operators.get(operators.size() - 1);
        }

        Logger.debug("PolicyGradient: selected " + selected.getSimpleName() +
                " (π=" + String.format("%.4f", policy[operators.indexOf(selected)]) + ")");

        postSelect(selected);
        return selected;
    }

    @Override
    public void updateQuality(Class<? extends Edit> operator, Long parentFitness,
                              Long childFitness, boolean success) {
        super.updateQuality(operator, parentFitness, childFitness, success);

        double reward = calculateReward(parentFitness, childFitness, success);
        int selectedIndex = operators.indexOf(operator);

        for (int i = 0; i < operators.size(); i++) {
            if (i == selectedIndex) {
                preferences[i] += alpha * (reward - averageReward) * (1 - policy[i]);
            } else {
                preferences[i] -= alpha * (reward - averageReward) * policy[i];
            }
        }

        policy = computeSoftmax(preferences);

        totalReward += reward;
        rewardCount++;
        averageReward = totalReward / rewardCount;

        preferencesLog.add(preferences.clone());
        policyLog.add(policy.clone());
        averageRewardLog.add(averageReward);

        Logger.debug("PolicyGradient: updated preferences, avg_reward=" +
                String.format("%.4f", averageReward));
    }

    public double[] getPolicy() {
        return policy.clone();
    }

    public Map<Class<? extends Edit>, Double> getPolicyMap() {
        Map<Class<? extends Edit>, Double> policyMap = new HashMap<>();
        for (int i = 0; i < operators.size(); i++) {
            policyMap.put(operators.get(i), policy[i]);
        }
        return policyMap;
    }

    public double[] getPreferences() {
        return preferences.clone();
    }

    public Map<Class<? extends Edit>, Double> getPreferencesMap() {
        Map<Class<? extends Edit>, Double> prefMap = new HashMap<>();
        for (int i = 0; i < operators.size(); i++) {
            prefMap.put(operators.get(i), preferences[i]);
        }
        return prefMap;
    }

    public double getAlpha() {
        return alpha;
    }

    public double getBaselineReward() {
        return averageReward;
    }

    public List<double[]> getPreferencesLog() {
        return Collections.unmodifiableList(preferencesLog);
    }

    public List<double[]> getPolicyLog() {
        return Collections.unmodifiableList(policyLog);
    }

    public List<Double> getAverageRewardLog() {
        return Collections.unmodifiableList(averageRewardLog);
    }

    @Override
    public void reset() {
        super.reset();

        Arrays.fill(preferences, 0.0);
        policy = computeSoftmax(preferences);

        averageReward = 0.0;
        totalReward = 0.0;
        rewardCount = 0;

        preferencesLog.clear();
        policyLog.clear();
        averageRewardLog.clear();

        preferencesLog.add(preferences.clone());
        policyLog.add(policy.clone());
        averageRewardLog.add(averageReward);
    }

    @Override
    public String toString() {
        return "PolicyGradientSelector{alpha=" + alpha +
                ", operators=" + operators.size() +
                ", avgReward=" + String.format("%.4f", averageReward) + "}";
    }
}
