"""
JUnit4: Compare all 5 experiments.

Exp 1: Random Sampling (baseline) — 5 reps, timestamp 004421
Exp 2: UCB + Traditional — 5 reps, timestamp 213836
Exp 3: UCB + Traditional + LLM — 3 reps, timestamp 044904
Exp 4: Standard LS + Traditional — 5 reps, timestamp 213836
Exp 5: Standard LS + Traditional + LLM — 3 reps, timestamp 044904

Produces:
  1. Grouped bar chart: Exp 3 vs Exp 5 (LLM experiments)
  2. Horizontal total summary: Exp 3 vs Exp 5
  3. Combined all-5 horizontal summary

Usage:
    python3 plot_junit4_all_experiments.py
"""

import csv, os, glob, argparse
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

# File patterns
EXP1_PATTERN = os.path.join(BASE, 'exp1_random_rep*_20260326_004421.csv')
EXP2_PATTERN = os.path.join(BASE, 'exp2_ucb_trad_rep*_20260325_213836.csv')
EXP3_PATTERN = os.path.join(BASE, 'exp3_ucb_all_rep*_20260329_044904.csv')
EXP4_PATTERN = os.path.join(BASE, 'exp4_ls_trad_rep*_20260325_213836.csv')
EXP5_PATTERN = os.path.join(BASE, 'exp5_ls_all_rep*_20260329_044904.csv')


def short_name(full_name):
    full_name = full_name.strip('"')
    paren = full_name.find('(')
    if paren == -1:
        return full_name.split('.')[-1]
    prefix = full_name[:paren]
    parts = prefix.split('.')
    method = parts[-1]
    class_name = parts[-2]
    if method == 'runnerForClass':
        return f'{class_name}.{method}'
    return method


def load_exp1(files):
    """Load RandomSampler CSVs."""
    results = defaultdict(list)
    for f in sorted(files):
        method_best = defaultdict(lambda: 0.0)
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = short_name(row['MethodName'])
                compiled = row['Compiled'].strip('"') == 'true'
                passed = row['AllTestsPassed'].strip('"') == 'true'
                baseline = float(row['BaselineRuntime(ms)'].strip('"'))
                patch_rt = float(row['PatchRuntime(ms)'].strip('"'))
                if compiled and passed and patch_rt > 0 and baseline > 0:
                    impr_pct = (baseline - patch_rt) / baseline * 100
                    if impr_pct > method_best[name]:
                        method_best[name] = impr_pct
        for m in method_best:
            results[m].append(method_best[m])
    return results


def load_local_search(files, runtime_col):
    """Load RLLocalSearch or LocalSearch CSVs (may have LLM prompt pollution)."""
    results = defaultdict(list)
    for f in sorted(files):
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            # Filter to valid CSV rows only (start with ")
            valid_lines = [line for line in fh if line.startswith('"')]

        import io
        reader = csv.DictReader(io.StringIO('\n'.join(valid_lines)))
        for row in reader:
            try:
                name = short_name(row['MethodName'])
                iteration = int(row['Iteration'].strip('"'))
                compiled = row['Compiled'].strip('"') == 'true'
                passed = row['AllTestsPassed'].strip('"') == 'true'
                rt = float(row[runtime_col].strip('"'))
            except (ValueError, KeyError, TypeError):
                continue

            if iteration == -1:
                if rt < 1e300:
                    method_baseline[name] = rt
                continue

            if name not in method_baseline:
                continue

            if compiled and passed and rt > 0 and rt < 1e300:
                if name not in method_best_rt or rt < method_best_rt[name]:
                    method_best_rt[name] = rt

        for m in method_baseline:
            bl = method_baseline[m]
            if m in method_best_rt:
                impr = (bl - method_best_rt[m]) / bl * 100
                results[m].append(max(impr, 0.0))
            else:
                results[m].append(0.0)
    return results


def compute_stats(exp_data, method_order):
    means, stds = [], []
    for m in method_order:
        vals = exp_data.get(m, [0])
        means.append(np.mean(vals))
        stds.append(np.std(vals))
    return means, stds


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    # Load all experiments
    exp1 = load_exp1(sorted(glob.glob(EXP1_PATTERN)))
    exp2 = load_local_search(sorted(glob.glob(EXP2_PATTERN)), 'Runtime(ms)')
    exp3 = load_local_search(sorted(glob.glob(EXP3_PATTERN)), 'Runtime(ms)')
    exp4 = load_local_search(sorted(glob.glob(EXP4_PATTERN)), 'Fitness')
    exp5 = load_local_search(sorted(glob.glob(EXP5_PATTERN)), 'Fitness')

    print(f'Files: Exp1={len(glob.glob(EXP1_PATTERN))}, Exp2={len(glob.glob(EXP2_PATTERN))}, '
          f'Exp3={len(glob.glob(EXP3_PATTERN))}, Exp4={len(glob.glob(EXP4_PATTERN))}, '
          f'Exp5={len(glob.glob(EXP5_PATTERN))}')

    all_methods = sorted(set(
        list(exp1.keys()) + list(exp2.keys()) + list(exp3.keys()) +
        list(exp4.keys()) + list(exp5.keys())
    ))
    # Sort by Exp 3 mean improvement descending
    method_order = sorted(all_methods, key=lambda m: -np.mean(exp3.get(m, [0])))

    # Print results table
    print(f'\n{"Method":<40} {"E1 Rand":<12} {"E2 UCB":<12} {"E3 UCB+LLM":<12} {"E4 LS":<12} {"E5 LS+LLM":<12}')
    print('-' * 100)

    csv_lines = ['Method,E1_mean,E1_std,E2_mean,E2_std,E3_mean,E3_std,E4_mean,E4_std,E5_mean,E5_std']

    for m in method_order:
        e1m, e1s = np.mean(exp1.get(m, [0])), np.std(exp1.get(m, [0]))
        e2m, e2s = np.mean(exp2.get(m, [0])), np.std(exp2.get(m, [0]))
        e3m, e3s = np.mean(exp3.get(m, [0])), np.std(exp3.get(m, [0]))
        e4m, e4s = np.mean(exp4.get(m, [0])), np.std(exp4.get(m, [0]))
        e5m, e5s = np.mean(exp5.get(m, [0])), np.std(exp5.get(m, [0]))
        print(f'{m:<40} {e1m:5.1f}±{e1s:4.1f}  {e2m:5.1f}±{e2s:4.1f}  {e3m:5.1f}±{e3s:4.1f}  {e4m:5.1f}±{e4s:4.1f}  {e5m:5.1f}±{e5s:4.1f}')
        csv_lines.append(f'{m},{e1m:.2f},{e1s:.2f},{e2m:.2f},{e2s:.2f},{e3m:.2f},{e3s:.2f},{e4m:.2f},{e4s:.2f},{e5m:.2f},{e5s:.2f}')

    # Totals
    e1_means, _ = compute_stats(exp1, method_order)
    e2_means, _ = compute_stats(exp2, method_order)
    e3_means, _ = compute_stats(exp3, method_order)
    e4_means, _ = compute_stats(exp4, method_order)
    e5_means, _ = compute_stats(exp5, method_order)

    t1, s1 = np.mean(e1_means), np.std(e1_means)
    t2, s2 = np.mean(e2_means), np.std(e2_means)
    t3, s3 = np.mean(e3_means), np.std(e3_means)
    t4, s4 = np.mean(e4_means), np.std(e4_means)
    t5, s5 = np.mean(e5_means), np.std(e5_means)

    print(f'{"TOTAL":<40} {t1:5.1f}±{s1:4.1f}  {t2:5.1f}±{s2:4.1f}  {t3:5.1f}±{s3:4.1f}  {t4:5.1f}±{s4:4.1f}  {t5:5.1f}±{s5:4.1f}')
    csv_lines.append(f'TOTAL,{t1:.2f},{s1:.2f},{t2:.2f},{s2:.2f},{t3:.2f},{s3:.2f},{t4:.2f},{s4:.2f},{t5:.2f},{s5:.2f}')

    # Save summary CSV
    csv_path = os.path.join(BASE, 'junit4_all_experiments_summary.csv')
    with open(csv_path, 'w') as f:
        f.write('JUnit4: All 5 Experiments Summary\n')
        f.write('Exp1: Random (5 reps), Exp2: UCB+Trad (5 reps), Exp3: UCB+All (3 reps), Exp4: LS+Trad (5 reps), Exp5: LS+All (3 reps)\n\n')
        f.write('\n'.join(csv_lines) + '\n')
    print(f'\nSaved: {csv_path}')

    # ---- Figure 1: Exp 3 vs Exp 5 per method ----
    e3_m, e3_s = compute_stats(exp3, method_order)
    e5_m, e5_s = compute_stats(exp5, method_order)

    fig1, ax1 = plt.subplots(figsize=(14, 6))
    x = np.arange(len(method_order))
    width = 0.35

    ax1.bar(x - width/2, e3_m, width, yerr=e3_s, capsize=3,
            label='Exp 3: UCB + All (Trad+LLM)', color='darkorchid', alpha=0.85)
    ax1.bar(x + width/2, e5_m, width, yerr=e5_s, capsize=3,
            label='Exp 5: Standard LS + All (Trad+LLM)', color='teal', alpha=0.85)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Best Improvement over Baseline (%)')
    ax1.set_title('JUnit4: UCB+LLM (Exp 3) vs Standard LS+LLM (Exp 5) — 3 reps, mean ± std')
    ax1.set_xticks(x)
    ax1.set_xticklabels(method_order, rotation=35, ha='right', fontsize=8)
    ax1.legend(fontsize=9)
    ax1.axhline(0, color='grey', linewidth=0.8, linestyle=':')
    ax1.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    out1 = os.path.join(BASE, 'junit4_exp3_vs_exp5_comparison.png')
    fig1.savefig(out1, dpi=150, bbox_inches='tight')
    print(f'Saved: {out1}')
    plt.close(fig1)

    # ---- Figure 2: Exp 3 vs Exp 5 total summary ----
    fig2, ax2 = plt.subplots(figsize=(8, 3.5))
    labels = ['Exp 3: UCB +\nAll (Trad+LLM)',
              'Exp 5: Standard LS\n+ All (Trad+LLM)']
    totals = [t3, t5]
    stds = [s3, s5]
    colors = ['darkorchid', 'teal']

    y = np.arange(len(labels))
    bars = ax2.barh(y, totals, xerr=stds, capsize=4, color=colors, alpha=0.85, height=0.4)
    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel('Mean Improvement over Baseline (%)')
    ax2.set_title('JUnit4: UCB+LLM vs LS+LLM — Mean Runtime Improvement (3 reps)')
    ax2.axvline(0, color='grey', linewidth=0.8)
    ax2.grid(True, axis='x', alpha=0.3)
    for bar, val, s in zip(bars, totals, stds):
        ax2.text(val + s + 0.3, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=11, fontweight='bold')
    plt.tight_layout()

    out2 = os.path.join(BASE, 'junit4_exp3_vs_exp5_total_summary.png')
    fig2.savefig(out2, dpi=150, bbox_inches='tight')
    print(f'Saved: {out2}')
    plt.close(fig2)

    # ---- Figure 3: All 5 experiments total summary ----
    fig3, ax3 = plt.subplots(figsize=(9, 5))
    labels_all = [
        'Exp 1: Random\nSampling',
        'Exp 2: UCB +\nTraditional',
        'Exp 3: UCB +\nAll (Trad+LLM)',
        'Exp 4: Standard LS\n+ Traditional',
        'Exp 5: Standard LS\n+ All (Trad+LLM)',
    ]
    totals_all = [t1, t2, t3, t4, t5]
    stds_all = [s1, s2, s3, s4, s5]
    colors_all = ['steelblue', 'darkorange', 'darkorchid', 'seagreen', 'teal']

    y = np.arange(len(labels_all))
    bars = ax3.barh(y, totals_all, xerr=stds_all, capsize=4, color=colors_all, alpha=0.85, height=0.5)
    ax3.set_yticks(y)
    ax3.set_yticklabels(labels_all, fontsize=10)
    ax3.set_xlabel('Mean Improvement over Baseline (%)')
    ax3.set_title('JUnit4: All Experiments — Mean Runtime Improvement Across Methods')
    ax3.axvline(0, color='grey', linewidth=0.8)
    ax3.grid(True, axis='x', alpha=0.3)
    for bar, val, s in zip(bars, totals_all, stds_all):
        ax3.text(val + s + 0.3, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=11, fontweight='bold')
    plt.tight_layout()

    out3 = os.path.join(BASE, 'junit4_all_experiments_summary.png')
    fig3.savefig(out3, dpi=150, bbox_inches='tight')
    print(f'Saved: {out3}')
    plt.close(fig3)


if __name__ == '__main__':
    main()
