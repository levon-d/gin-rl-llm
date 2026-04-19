"""
JUnit4: Compare Exp 1 (Random) vs Exp 2 (UCB+Trad) vs Exp 4 (LS+Trad).

Reads raw CSV files, computes per-method best improvement (%) across reps,
and generates:
  1. Grouped bar chart per method (mean ± std across reps)
  2. Horizontal bar chart: TOTAL mean improvement per experiment

Usage:
    python3 plot_junit4_exp1_exp2_exp4.py
    python3 plot_junit4_exp1_exp2_exp4.py --show
"""

import csv, os, glob, argparse
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

# --- File patterns ---
EXP1_PATTERN = os.path.join(BASE, 'exp1_random_rep*_20260326_004421.csv')
EXP2_PATTERN = os.path.join(BASE, 'exp2_ucb_trad_rep*_20260325_213836.csv')
EXP4_PATTERN = os.path.join(BASE, 'exp4_ls_trad_rep*_20260325_213836.csv')

# Short display names (ClassName.method for disambiguation)
def short_name(full_name):
    """Extract ClassName.methodName from the full qualified name.

    Handles two formats:
      - pkg.ClassName.methodName(args)           (RandomSampler)
      - pkg.ClassName.pkg.ClassName.methodName(args)  (LocalSearch/RLLocalSearch)
    """
    full_name = full_name.strip('"')
    paren = full_name.find('(')
    if paren == -1:
        return full_name.split('.')[-1]
    prefix = full_name[:paren]
    parts = prefix.split('.')
    method = parts[-1]
    class_name = parts[-2]
    # Special case: runnerForClass appears in two classes
    if method == 'runnerForClass':
        return f'{class_name}.{method}'
    return method


def load_exp1(files):
    """Load RandomSampler CSVs. Returns {method: [best_impr_pct_per_rep]}."""
    results = defaultdict(list)
    for f in sorted(files):
        method_best = defaultdict(lambda: 0.0)
        method_baseline = {}
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = short_name(row['MethodName'])
                compiled = row['Compiled'].strip('"') == 'true'
                passed = row['AllTestsPassed'].strip('"') == 'true'
                baseline = float(row['BaselineRuntime(ms)'].strip('"'))
                patch_rt = float(row['PatchRuntime(ms)'].strip('"'))
                method_baseline[name] = baseline
                if compiled and passed and patch_rt > 0 and baseline > 0:
                    impr_pct = (baseline - patch_rt) / baseline * 100
                    if impr_pct > method_best[name]:
                        method_best[name] = impr_pct
        for m in method_best:
            results[m].append(method_best[m])
    return results


def load_exp2_or_4(files, runtime_col):
    """Load RLLocalSearch or LocalSearch CSVs.
    runtime_col: 'Runtime(ms)' for Exp2, 'Fitness' for Exp4.
    Returns {method: [best_impr_pct_per_rep]}.
    """
    results = defaultdict(list)
    for f in sorted(files):
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = short_name(row['MethodName'])
                iteration = int(row['Iteration'].strip('"'))
                compiled = row['Compiled'].strip('"') == 'true'
                passed = row['AllTestsPassed'].strip('"') == 'true'
                rt = float(row[runtime_col].strip('"'))

                if iteration == -1:
                    # Baseline row
                    if rt < 1e300:  # filter broken baselines
                        method_baseline[name] = rt
                    continue

                if name not in method_baseline:
                    continue  # skip if baseline was broken

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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    exp1_files = sorted(glob.glob(EXP1_PATTERN))
    exp2_files = sorted(glob.glob(EXP2_PATTERN))
    exp4_files = sorted(glob.glob(EXP4_PATTERN))

    print(f'Exp 1 files: {len(exp1_files)}, Exp 2 files: {len(exp2_files)}, Exp 4 files: {len(exp4_files)}')

    exp1 = load_exp1(exp1_files)
    exp2 = load_exp2_or_4(exp2_files, 'Runtime(ms)')
    exp4 = load_exp2_or_4(exp4_files, 'Fitness')

    # Get all methods, sorted by Exp 2 mean improvement (descending)
    all_methods = sorted(set(list(exp1.keys()) + list(exp2.keys()) + list(exp4.keys())))
    method_order = sorted(all_methods, key=lambda m: -np.mean(exp2.get(m, [0])))

    print(f'\n{"Method":<40} {"Exp1(Random)":<18} {"Exp2(UCB)":<18} {"Exp4(LS)":<18}')
    print('-' * 94)

    # Summary CSV
    csv_lines = ['Method,Impr_E1_mean(%),Impr_E1_std(%),Impr_E2_mean(%),Impr_E2_std(%),Impr_E4_mean(%),Impr_E4_std(%),Winner']

    e1_means, e1_stds = [], []
    e2_means, e2_stds = [], []
    e4_means, e4_stds = [], []

    for m in method_order:
        e1_vals = exp1.get(m, [0])
        e2_vals = exp2.get(m, [0])
        e4_vals = exp4.get(m, [0])

        e1_m, e1_s = np.mean(e1_vals), np.std(e1_vals)
        e2_m, e2_s = np.mean(e2_vals), np.std(e2_vals)
        e4_m, e4_s = np.mean(e4_vals), np.std(e4_vals)

        e1_means.append(e1_m); e1_stds.append(e1_s)
        e2_means.append(e2_m); e2_stds.append(e2_s)
        e4_means.append(e4_m); e4_stds.append(e4_s)

        best = max(e1_m, e2_m, e4_m)
        winner = 'Random' if best == e1_m else ('UCB' if best == e2_m else 'LS')
        print(f'{m:<40} {e1_m:6.2f}±{e1_s:5.2f}    {e2_m:6.2f}±{e2_s:5.2f}    {e4_m:6.2f}±{e4_s:5.2f}    {winner}')
        csv_lines.append(f'{m},{e1_m:.2f},{e1_s:.2f},{e2_m:.2f},{e2_s:.2f},{e4_m:.2f},{e4_s:.2f},{winner}')

    # Totals
    t1_m, t1_s = np.mean(e1_means), np.std(e1_means)
    t2_m, t2_s = np.mean(e2_means), np.std(e2_means)
    t4_m, t4_s = np.mean(e4_means), np.std(e4_means)
    winner = 'Random' if t1_m >= max(t2_m, t4_m) else ('UCB' if t2_m >= t4_m else 'LS')
    print(f'{"TOTAL (mean of methods)":<40} {t1_m:6.2f}±{t1_s:5.2f}    {t2_m:6.2f}±{t2_s:5.2f}    {t4_m:6.2f}±{t4_s:5.2f}    {winner}')
    csv_lines.append(f'TOTAL,{t1_m:.2f},{t1_s:.2f},{t2_m:.2f},{t2_s:.2f},{t4_m:.2f},{t4_s:.2f},{winner}')

    # Write summary CSV
    csv_path = os.path.join(BASE, 'junit4_exp1_exp2_exp4_summary.csv')
    with open(csv_path, 'w') as f:
        f.write('JUnit4: Exp 1 (Random) vs Exp 2 (UCB+Traditional) vs Exp 4 (Standard LS+Traditional) — 5 reps each\n\n')
        f.write('\n'.join(csv_lines) + '\n')
    print(f'\nSaved: {csv_path}')

    # ---- Figure 1: Grouped bar chart per method ----
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    x = np.arange(len(method_order))
    width = 0.25

    ax1.bar(x - width, e1_means, width, yerr=e1_stds, capsize=3,
            label='Exp 1: Random Sampling', color='steelblue', alpha=0.85)
    ax1.bar(x, e2_means, width, yerr=e2_stds, capsize=3,
            label='Exp 2: UCB + Traditional', color='darkorange', alpha=0.85)
    ax1.bar(x + width, e4_means, width, yerr=e4_stds, capsize=3,
            label='Exp 4: Standard LS + Traditional', color='seagreen', alpha=0.85)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Best Improvement over Baseline (%)')
    ax1.set_title('JUnit4: Best Runtime Improvement per Method (5 reps, mean ± std)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(method_order, rotation=35, ha='right', fontsize=8)
    ax1.legend(fontsize=9)
    ax1.axhline(0, color='grey', linewidth=0.8, linestyle=':')
    ax1.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out1 = os.path.join(BASE, 'junit4_exp1_exp2_exp4_comparison.png')
        fig1.savefig(out1, dpi=150, bbox_inches='tight')
        print(f'Saved: {out1}')
    plt.close(fig1)

    # ---- Figure 2: Horizontal bar — TOTAL improvement ----
    fig2, ax2 = plt.subplots(figsize=(8, 4))
    labels = ['Exp 1: Random\nSampling',
              'Exp 2: UCB +\nTraditional',
              'Exp 4: Standard LS\n+ Traditional']
    totals = [t1_m, t2_m, t4_m]
    stds = [t1_s, t2_s, t4_s]
    colors = ['steelblue', 'darkorange', 'seagreen']

    y = np.arange(len(labels))
    bars = ax2.barh(y, totals, xerr=stds, capsize=4, color=colors, alpha=0.85, height=0.45)

    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel('Mean Improvement over Baseline (%)')
    ax2.set_title('JUnit4: Mean Runtime Improvement Across Methods (5 reps)')
    ax2.axvline(0, color='grey', linewidth=0.8)
    ax2.grid(True, axis='x', alpha=0.3)

    for bar, val, s in zip(bars, totals, stds):
        ax2.text(val + s + 0.3, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=11, fontweight='bold')

    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out2 = os.path.join(BASE, 'junit4_exp1_exp2_exp4_total_summary.png')
        fig2.savefig(out2, dpi=150, bbox_inches='tight')
        print(f'Saved: {out2}')
    plt.close(fig2)


if __name__ == '__main__':
    main()
