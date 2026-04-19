"""
JUnit4 500 steps: Compare Exp 2 (UCB+Trad) vs Exp 4 (LS+Trad).

Usage:
    python3 plot_junit4_exp2_exp4_500steps.py
    python3 plot_junit4_exp2_exp4_500steps.py --show
"""

import csv, os, glob, argparse
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

EXP2_PATTERN = os.path.join(BASE, 'exp2_ucb_trad_rep*_*.csv')
EXP4_PATTERN = os.path.join(BASE, 'exp4_ls_trad_rep*_*.csv')


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


def load_exp(files, runtime_col):
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    exp2_files = sorted(glob.glob(EXP2_PATTERN))
    exp4_files = sorted(glob.glob(EXP4_PATTERN))

    print(f'Exp 2 files: {len(exp2_files)}, Exp 4 files: {len(exp4_files)}')

    exp2 = load_exp(exp2_files, 'Runtime(ms)')
    exp4 = load_exp(exp4_files, 'Fitness')

    all_methods = sorted(set(list(exp2.keys()) + list(exp4.keys())))
    method_order = sorted(all_methods, key=lambda m: -np.mean(exp2.get(m, [0])))

    print(f'\n{"Method":<45} {"Exp2(UCB)":<18} {"Exp4(LS)":<18} {"Winner"}')
    print('-' * 90)

    csv_lines = ['Method,Impr_E2_mean(%),Impr_E2_std(%),Impr_E4_mean(%),Impr_E4_std(%),Winner']

    e2_means, e2_stds = [], []
    e4_means, e4_stds = [], []

    for m in method_order:
        e2_vals = exp2.get(m, [0])
        e4_vals = exp4.get(m, [0])

        e2_m, e2_s = np.mean(e2_vals), np.std(e2_vals)
        e4_m, e4_s = np.mean(e4_vals), np.std(e4_vals)

        e2_means.append(e2_m); e2_stds.append(e2_s)
        e4_means.append(e4_m); e4_stds.append(e4_s)

        winner = 'UCB' if e2_m >= e4_m else 'LS'
        print(f'{m:<45} {e2_m:6.2f}±{e2_s:5.2f}    {e4_m:6.2f}±{e4_s:5.2f}    {winner}')
        csv_lines.append(f'{m},{e2_m:.2f},{e2_s:.2f},{e4_m:.2f},{e4_s:.2f},{winner}')

    t2_m, t2_s = np.mean(e2_means), np.std(e2_means)
    t4_m, t4_s = np.mean(e4_means), np.std(e4_means)
    winner = 'UCB' if t2_m >= t4_m else 'LS'
    print(f'{"TOTAL (mean of methods)":<45} {t2_m:6.2f}±{t2_s:5.2f}    {t4_m:6.2f}±{t4_s:5.2f}    {winner}')
    csv_lines.append(f'TOTAL,{t2_m:.2f},{t2_s:.2f},{t4_m:.2f},{t4_s:.2f},{winner}')

    # Also compare with 100-step results
    print(f'\n--- Comparison with 100-step results ---')
    print(f'100 steps: UCB 13.7%, LS 16.3% (LS wins)')
    print(f'500 steps: UCB {t2_m:.1f}%, LS {t4_m:.1f}% ({winner} wins)')

    csv_path = os.path.join(BASE, 'junit4_exp2_vs_exp4_500steps_summary.csv')
    with open(csv_path, 'w') as f:
        f.write('JUnit4: Exp 2 (UCB+Traditional) vs Exp 4 (Standard LS+Traditional) — 500 steps, 5 reps\n\n')
        f.write('\n'.join(csv_lines) + '\n')
    print(f'\nSaved: {csv_path}')

    # ---- Figure 1: Grouped bar chart per method ----
    fig1, ax1 = plt.subplots(figsize=(14, 6))
    x = np.arange(len(method_order))
    width = 0.35

    ax1.bar(x - width/2, e2_means, width, yerr=e2_stds, capsize=3,
            label='Exp 2: UCB + Traditional', color='darkorange', alpha=0.85)
    ax1.bar(x + width/2, e4_means, width, yerr=e4_stds, capsize=3,
            label='Exp 4: Standard LS + Traditional', color='seagreen', alpha=0.85)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Best Improvement over Baseline (%)')
    ax1.set_title('JUnit4 (500 steps): Best Runtime Improvement per Method (5 reps, mean ± std)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(method_order, rotation=35, ha='right', fontsize=8)
    ax1.legend(fontsize=9)
    ax1.axhline(0, color='grey', linewidth=0.8, linestyle=':')
    ax1.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out1 = os.path.join(BASE, 'junit4_exp2_vs_exp4_500steps_comparison.png')
        fig1.savefig(out1, dpi=150, bbox_inches='tight')
        print(f'Saved: {out1}')
    plt.close(fig1)

    # ---- Figure 2: Horizontal bar — TOTAL improvement ----
    fig2, ax2 = plt.subplots(figsize=(8, 3.5))
    labels = ['Exp 2: UCB +\nTraditional (500 steps)',
              'Exp 4: Standard LS\n+ Traditional (500 steps)']
    totals = [t2_m, t4_m]
    stds = [t2_s, t4_s]
    colors = ['darkorange', 'seagreen']

    y = np.arange(len(labels))
    bars = ax2.barh(y, totals, xerr=stds, capsize=4, color=colors, alpha=0.85, height=0.4)

    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel('Mean Improvement over Baseline (%)')
    ax2.set_title('JUnit4 (500 steps): Mean Runtime Improvement Across Methods (5 reps)')
    ax2.axvline(0, color='grey', linewidth=0.8)
    ax2.grid(True, axis='x', alpha=0.3)

    for bar, val, s in zip(bars, totals, stds):
        ax2.text(val + s + 0.3, bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=11, fontweight='bold')

    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out2 = os.path.join(BASE, 'junit4_exp2_vs_exp4_500steps_total_summary.png')
        fig2.savefig(out2, dpi=150, bbox_inches='tight')
        print(f'Saved: {out2}')
    plt.close(fig2)


if __name__ == '__main__':
    main()
