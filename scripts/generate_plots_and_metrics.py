#!/usr/bin/env python3
"""
Task 1: UCB Convergence Plot (400-step RL log)
Task 2: Metric B Standard Deviations across experiments
"""

import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import warnings

import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

BASE = "/Users//repos/gin-rl/experiment_results/runtime_wang_top10"
BASE_400 = "/Users//repos/gin-rl/experiment_results/runtime_wang_top10_400steps"

print("=" * 60)
print("TASK 1: UCB Convergence Plot")
print("=" * 60)
MAIN_LOG = os.path.join(BASE_400, "exp3_rl_log_400steps_rep1_20260410_115033.csv")
REMAINING_LOG = os.path.join(
    BASE_400, "exp3_rl_log_400steps_remaining_20260412_134757.csv"
)
FILTERBS4_LOG = os.path.join(
    BASE_400, "exp3_rl_log_400steps_filterbs4_20260412_174512.csv"
)

METHOD_NAMES = {
    1: "filterBs",
    2: "estimateQPix",
    3: "takeSafe",
    4: "getLumaPred4x4",
    5: "filterBlockEdgeHoris",
    6: "filterBlockEdgeVert",
    7: "filterBs4",
    8: "mergeResidual",
    9: "resample",
    10: "getPlaneWidth",
}

parts = []

df_main = pd.read_csv(MAIN_LOG, on_bad_lines="skip")
local_to_global_main = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 8: 8}  # skip 7 and 9
for local_id, global_id in local_to_global_main.items():
    chunk = df_main[df_main["MethodID"] == local_id].copy()
    chunk["MethodID"] = global_id
    chunk["MethodName"] = METHOD_NAMES[global_id]
    parts.append(chunk)

df_rem = pd.read_csv(REMAINING_LOG, on_bad_lines="skip")
for local_id, global_id in {1: 9, 2: 10}.items():
    chunk = df_rem[df_rem["MethodID"] == local_id].copy()
    chunk["MethodID"] = global_id
    chunk["MethodName"] = METHOD_NAMES[global_id]
    parts.append(chunk)

df_fb4 = pd.read_csv(FILTERBS4_LOG, on_bad_lines="skip")
chunk = df_fb4[df_fb4["MethodID"] == 1].copy()
chunk["MethodID"] = 7
chunk["MethodName"] = METHOD_NAMES[7]
parts.append(chunk)

rl = pd.concat(parts, ignore_index=True)
print(f"Combined RL log shape: {rl.shape}")
print(f"Steps per method:\n{rl.groupby('MethodID')['Step'].count().sort_index()}")

steps_per_method = rl.groupby("MethodID")["Step"].count()


def method_operator_reward_variance(grp):
    op_means = grp.groupby("Operator")["Reward"].mean()
    return op_means.var() if len(op_means) > 1 else 0.0


variance_per_method = rl.groupby("MethodID").apply(method_operator_reward_variance)
print(
    f"\nReward variance across operators per method:\n{variance_per_method.sort_values(ascending=False)}"
)

best_method = 6
best_name = METHOD_NAMES[best_method]
print(
    f"\nSelected method: {best_name} (ID={best_method}, {steps_per_method[best_method]} steps)"
)

method_data = rl[rl["MethodID"] == best_method].copy()

method_data = method_data.sort_values("Step").reset_index(drop=True)

operators = sorted(method_data["Operator"].unique())
print(f"Operators for this method: {operators}")

fig, ax = plt.subplots(figsize=(10, 6))

colors = plt.cm.tab10(np.linspace(0, 1, min(len(operators), 10)))

for i, op in enumerate(operators):
    op_data = method_data[method_data["Operator"] == op].sort_values("Step")
    steps = op_data["Step"].values
    rewards = op_data["Reward"].values
    cum_means = np.cumsum(rewards) / np.arange(1, len(rewards) + 1)
    ax.plot(
        steps,
        cum_means,
        label=op,
        color=colors[i % len(colors)],
        linewidth=1.5,
        alpha=0.85,
    )

ax.set_xlabel("Search Step", fontsize=13)
ax.set_ylabel("Cumulative Mean Reward", fontsize=13)
ax.set_title(
    f"UCB Q-Value Estimates Over Search Steps\n(400-step run, jcodec, method: {best_name})",
    fontsize=13,
)
ax.legend(title="Operator", fontsize=8, title_fontsize=9, loc="best", ncol=1)
ax.grid(True, alpha=0.3)
plt.tight_layout()

out_path = "/Users//repos/gin-rl/experiment_results/ucb_convergence_400steps.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"\nPlot saved to: {out_path}")

print("\n" + "=" * 60)
print("TASK 2: Metric B Standard Deviations")
print("=" * 60)

JCODEC_METHODS_SHORT = [
    "filterBs4",
    "filterBs",
    "estimateQPix",
    "takeSafe",
    "getLumaPred4x4",
    "filterBlockEdgeHoris",
    "filterBlockEdgeVert",
    "mergeResidual",
    "resample",
    "getPlaneWidth",
]


def method_matches(mname):
    """Check if method name contains any of the jcodec target methods."""
    for m in JCODEC_METHODS_SHORT:
        if m in mname:
            return True
    return False


def get_method_short(mname):
    """Return the short name of the matched method."""
    for m in JCODEC_METHODS_SHORT:
        if m in mname:
            return m
    return None


def compute_metric_b_for_file(fpath, fmt):
    """
    Compute per-method ratio = best_passing_rt / baseline_rt * 100.
    Returns dict: method_short -> ratio (or 100 if no passing patches).

    fmt: 'random'   -> PatchIndex,MethodName,MethodID,Operator,Patch,Compiled,AllTestsPassed,
                        BaselineRuntime(ms),PatchRuntime(ms),RuntimeImprovement(ms),ImprovementPercent
         'ucb_trad' -> MethodName,Iteration,EvaluationNumber,Patch,Compiled,AllTestsPassed,
                        TotalExecutionTime(ms),Runtime(ms),RuntimeImprovement(ms)
         'gp'       -> MethodName,Iteration,EvaluationNumber,Patch,Compiled,AllTestsPassed,
                        TotalExecutionTime(ms),Fitness,FitnessImprovement
    """
    try:
        df = pd.read_csv(fpath, quotechar='"')
        df.columns = [c.strip().strip('"') for c in df.columns]

        for col in df.select_dtypes(include="object").columns:
            df[col] = df[col].astype(str).str.strip().str.strip('"')

    except Exception as e:
        print(f"  ERROR reading {fpath}: {e}")
        return {}

    ratios = {}

    if fmt == "random":
        df = df[df["MethodName"].apply(method_matches)].copy()
        df["mshort"] = df["MethodName"].apply(get_method_short)

        for col in ["BaselineRuntime(ms)", "PatchRuntime(ms)"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        for mshort, grp in df.groupby("mshort"):
            bl_vals = pd.to_numeric(
                grp["BaselineRuntime(ms)"], errors="coerce"
            ).dropna()
            baseline = bl_vals.iloc[0] if len(bl_vals) > 0 else None
            if baseline is None or baseline <= 0:
                ratios[mshort] = 100.0
                continue

            compiled_mask = grp["Compiled"].apply(
                lambda x: str(x).strip().strip('"').lower() == "true"
            )
            atp_mask = grp["AllTestsPassed"].apply(
                lambda x: str(x).strip().strip('"').lower() == "true"
            )
            passing = grp[compiled_mask & atp_mask]["PatchRuntime(ms)"].dropna()

            valid = passing[(passing > 0) & (passing < 1e300)]
            if len(valid) == 0:
                ratios[mshort] = 100.0
            else:
                best = valid.min()
                ratios[mshort] = (best / baseline) * 100.0

    else:
        if fmt == "ucb_trad":
            rt_col = "Runtime(ms)"
        else:
            rt_col = "Fitness"

        df = df[df["MethodName"].apply(method_matches)].copy()
        df["mshort"] = df["MethodName"].apply(get_method_short)
        df["Iteration"] = pd.to_numeric(df["Iteration"], errors="coerce")
        df[rt_col] = pd.to_numeric(df[rt_col], errors="coerce")

        for mshort, grp in df.groupby("mshort"):
            baseline_rows = grp[grp["Iteration"] == -1]
            if len(baseline_rows) == 0:
                ratios[mshort] = 100.0
                continue
            baseline = baseline_rows[rt_col].dropna().mean()
            if baseline is None or baseline <= 0 or pd.isna(baseline):
                ratios[mshort] = 100.0
                continue

            patches = grp[grp["Iteration"] > -1]
            compiled_mask = patches["Compiled"].apply(
                lambda x: str(x).strip().strip('"').lower() == "true"
            )
            atp_mask = patches["AllTestsPassed"].apply(
                lambda x: str(x).strip().strip('"').lower() == "true"
            )
            passing = patches[compiled_mask & atp_mask][rt_col].dropna()

            valid = passing[(passing > 0) & (passing < 1e300)]
            if len(valid) == 0:
                ratios[mshort] = 100.0
            else:
                best = valid.min()
                ratios[mshort] = (best / baseline) * 100.0

    return ratios


def per_rep_score(ratios_dict):
    """Mean ratio across all 10 jcodec methods. Missing -> 100."""
    vals = []
    for m in JCODEC_METHODS_SHORT:
        vals.append(ratios_dict.get(m, 100.0))
    return np.mean(vals)


exp1_files = {
    "rep1": os.path.join(BASE, "exp1_random_rep1_20260316_124805.csv"),
    "rep2": os.path.join(BASE, "exp1_random_rep2_20260316_124805.csv"),
    "rep3": os.path.join(BASE, "exp1_random_rep3_20260312_143630.csv"),
    "rep4": os.path.join(BASE, "exp1_random_rep4_20260312_143630.csv"),
    "rep5": os.path.join(BASE, "exp1_random_rep5_20260312_143630.csv"),
}
exp2_files = {
    "rep1": os.path.join(BASE, "exp2_ucb_trad_rep1_20260312_143630.csv"),
    "rep2": os.path.join(BASE, "exp2_ucb_trad_rep2_20260312_143630.csv"),
    "rep3": os.path.join(BASE, "exp2_ucb_trad_rep3_20260312_143630.csv"),
    "rep4": os.path.join(BASE, "exp2_ucb_trad_rep4_20260312_143630.csv"),
    "rep5": os.path.join(BASE, "exp2_ucb_trad_rep5_20260312_143630.csv"),
}
exp3_files = {
    "rep1": os.path.join(BASE, "exp3_ucb_all_rep1_20260316_230008.csv"),
    "rep2": os.path.join(BASE, "exp3_ucb_all_rep2_20260330_001857.csv"),
    "rep3": os.path.join(BASE, "exp3_ucb_all_rep3_20260330_001857.csv"),
    "rep4": os.path.join(BASE, "exp3_ucb_all_rep4_20260408_201948.csv"),
    "rep5": os.path.join(BASE, "exp3_ucb_all_rep5_20260408_201948.csv"),
}
exp4_files = {
    "rep1": os.path.join(BASE, "exp4_ls_trad_rep1_20260319_123900.csv"),
    "rep2": os.path.join(BASE, "exp4_ls_trad_rep2_20260319_123900.csv"),
    "rep3": os.path.join(BASE, "exp4_ls_trad_rep3_20260319_123900.csv"),
    "rep4": os.path.join(BASE, "exp4_ls_trad_rep4_20260319_123900.csv"),
    "rep5": os.path.join(BASE, "exp4_ls_trad_rep5_20260319_123900.csv"),
}
exp5_files = {
    "rep1": os.path.join(BASE, "exp5_ls_all_rep1_20260323_140041.csv"),
    "rep2": os.path.join(BASE, "exp5_ls_all_rep2_20260331_152947.csv"),
    "rep3": os.path.join(BASE, "exp5_ls_all_rep3_20260401_141651.csv"),
    "rep4": os.path.join(BASE, "exp5_ls_all_rep4_cal_pb08_20260409_212652.csv"),
    "rep5": os.path.join(BASE, "exp5_ls_all_rep5_cal_pb08_20260409_151823.csv"),
}

experiments = [
    ("Exp1 (Random)", exp1_files, "random"),
    ("Exp2 (UCB+Trad)", exp2_files, "ucb_trad"),
    ("Exp3 (UCB+All)", exp3_files, "ucb_trad"),
    ("Exp4 (LS+Trad)", exp4_files, "gp"),
    ("Exp5 (LS+All)", exp5_files, "gp"),
]

print("\nComputing Metric B (mean runtime ratio % across 10 methods, lower = better)\n")
print(
    f"{'Experiment':<22} {'Rep1':>8} {'Rep2':>8} {'Rep3':>8} {'Rep4':>8} {'Rep5':>8}  {'Mean':>8} {'SD':>8}"
)
print("-" * 90)

summary_rows = []
for exp_name, files_dict, fmt in experiments:
    rep_scores = []
    rep_details = []
    for rep, fpath in files_dict.items():
        if not os.path.exists(fpath):
            print(f"  WARNING: {fpath} not found, using 100 for all methods")
            score = 100.0
            details = {m: 100.0 for m in JCODEC_METHODS_SHORT}
        else:
            details = compute_metric_b_for_file(fpath, fmt)
            score = per_rep_score(details)
        rep_scores.append(score)
        rep_details.append(details)

    mean_score = np.mean(rep_scores)
    sd_score = np.std(rep_scores, ddof=1)

    row_str = f"{exp_name:<22}"
    for s in rep_scores:
        row_str += f" {s:>8.2f}"
    row_str += f"  {mean_score:>8.2f} {sd_score:>8.2f}"
    print(row_str)

    summary_rows.append((exp_name, rep_scores, mean_score, sd_score))

print("\n")
print("=" * 60)
print("FINAL RESULTS (Metric B: Mean Runtime Ratio %, lower = better)")
print("=" * 60)
for exp_name, rep_scores, mean_score, sd_score in summary_rows:
    print(
        f"{exp_name:<22}: {mean_score:.2f} ± {sd_score:.2f}  (reps: {[round(s, 2) for s in rep_scores]})"
    )

print("\n")
print("Per-method breakdown (mean across reps for each method):")
print("-" * 70)
for exp_name, files_dict, fmt in experiments:
    print(f"\n{exp_name}:")
    method_rep_ratios = {m: [] for m in JCODEC_METHODS_SHORT}
    for rep, fpath in files_dict.items():
        if not os.path.exists(fpath):
            for m in JCODEC_METHODS_SHORT:
                method_rep_ratios[m].append(100.0)
        else:
            details = compute_metric_b_for_file(fpath, fmt)
            for m in JCODEC_METHODS_SHORT:
                method_rep_ratios[m].append(details.get(m, 100.0))
    for m in JCODEC_METHODS_SHORT:
        vals = method_rep_ratios[m]
        print(f"  {m:<25}: {np.mean(vals):.2f}%  (reps: {[round(v, 2) for v in vals]})")

print("\nDone.")
