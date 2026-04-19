"""
Plot Exp 1 vs Exp 2 comparison charts.

Produces two figures:
  1. Bar chart: mean improvement % per method (Exp1 vs Exp2)
  2. Bar chart: operator selection frequency in Exp 2 (UCB learned preferences)

Usage:
    python3 plot_comparison.py
    python3 plot_comparison.py --timestamp 20260308_004051
    python3 plot_comparison.py --show
"""

import csv, os, glob, argparse
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

METHODS_ORDER = [
    'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'filterBs4',
    'mergeResidual', 'resample', 'getPlaneWidth',
]


def short_name(full_name):
    for key in METHODS_ORDER:
        if key.rstrip('(') in full_name:
            return key
    return full_name


def load_exp1_best(timestamp):
    """Returns dict: short_name -> list of improvement % across reps (best patch found)."""
    results = defaultdict(list)
    files = sorted(glob.glob(BASE + f'/exp1_random_rep*_{timestamp}.csv'))
    for f in files:
        method_best = {}
        method_baseline = {}
        with open(f) as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                passed = row['AllTestsPassed'].strip().lower() == 'true'
                short = short_name(row['MethodName'].strip())
                baseline = float(row['BaselineRuntime(ms)'])
                patch_rt = float(row['PatchRuntime(ms)'])
                method_baseline[short] = baseline
                if passed and patch_rt > 0 and patch_rt < baseline:
                    if short not in method_best or patch_rt < method_best[short]:
                        method_best[short] = patch_rt
        for short in METHODS_ORDER:
            bl = method_baseline.get(short, 0)
            best = method_best.get(short, bl)
            pct = 100.0 * (bl - best) / bl if bl > 0 else 0.0
            results[short].append(pct)
    return results


def load_exp2_best(timestamp):
    """Returns dict: short_name -> list of improvement % across reps (from runtime summary)."""
    results = defaultdict(list)
    files = sorted(glob.glob(BASE + f'/exp2_rl_log_rep*_{timestamp}_runtime_summary.csv'))
    for f in files:
        with open(f) as fh:
            reader = csv.reader(fh)
            next(reader)
            for row in reader:
                name = row[0].strip('"')
                if name == 'TOTAL':
                    continue
                short = short_name(name)
                results[short].append(float(row[4]))
    return results


def load_operator_usage(timestamp):
    """Returns dict: operator -> (attempts, successes) aggregated across all reps."""
    usage = defaultdict(lambda: [0, 0])
    files = sorted(glob.glob(BASE + f'/exp2_rl_log_rep*_{timestamp}.csv'))
    if not files:
        files = sorted(f for f in glob.glob(BASE + f'/exp2_rl_log_rep*_{timestamp}*.csv')
                       if 'summary' not in f and 'runtime' not in f)
    for f in files:
        with open(f) as fh:
            reader = csv.reader(fh)
            next(reader)
            for row in reader:
                op = row[2].strip()
                success = row[3].strip().lower() == 'true'
                usage[op][0] += 1
                if success:
                    usage[op][1] += 1
    return usage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timestamp', default=None)
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    # Infer timestamp
    if args.timestamp:
        timestamp = args.timestamp
    else:
        files = glob.glob(BASE + '/exp1_random_rep1_*.csv')
        files = [f for f in files if 'summary' not in f]
        if not files:
            print('No Exp 1 files found.')
            return
        latest = sorted(files)[-1]
        timestamp = '_'.join(os.path.basename(latest).replace('.csv', '').split('_')[-2:])
    print(f'Using timestamp: {timestamp}')

    exp1 = load_exp1_best(timestamp)
    exp2 = load_exp2_best(timestamp)
    op_usage = load_operator_usage(timestamp)

    # ---- Figure 1: Per-method improvement comparison ----
    fig1, ax1 = plt.subplots(figsize=(13, 5))

    x = np.arange(len(METHODS_ORDER))
    width = 0.35

    e1_means = [np.mean(exp1.get(m, [0])) for m in METHODS_ORDER]
    e1_stds  = [np.std(exp1.get(m, [0])) for m in METHODS_ORDER]
    e2_means = [np.mean(exp2.get(m, [0])) for m in METHODS_ORDER]
    e2_stds  = [np.std(exp2.get(m, [0])) for m in METHODS_ORDER]

    bars1 = ax1.bar(x - width/2, e1_means, width, yerr=e1_stds,
                    label='Exp 1: Random Sampling', color='steelblue',
                    alpha=0.8, capsize=4)
    bars2 = ax1.bar(x + width/2, e2_means, width, yerr=e2_stds,
                    label='Exp 2: UCB (Traditional)', color='darkorange',
                    alpha=0.8, capsize=4)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Mean improvement over baseline (%)')
    ax1.set_title('Best Improvement Found: Random Sampling vs UCB Local Search\n(mean ± std across repetitions)')
    ax1.set_xticks(x)
    ax1.set_xticklabels(METHODS_ORDER, rotation=30, ha='right', fontsize=9)
    ax1.legend()
    ax1.axhline(0, color='grey', linewidth=0.8, linestyle=':')
    ax1.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out1 = BASE + f'/exp1_vs_exp2_improvement_{timestamp}.png'
        fig1.savefig(out1, dpi=150, bbox_inches='tight')
        print(f'Saved: {out1}')

    # ---- Figure 2: Operator usage in Exp 2 ----
    if op_usage:
        fig2, (ax2a, ax2b) = plt.subplots(1, 2, figsize=(13, 5))

        ops = sorted(op_usage.keys())
        attempts = [op_usage[op][0] for op in ops]
        successes = [op_usage[op][1] for op in ops]
        success_rates = [100.0 * s / a if a > 0 else 0 for s, a in zip(successes, attempts)]

        y = np.arange(len(ops))

        # Attempts
        ax2a.barh(y, attempts, color='steelblue', alpha=0.8)
        ax2a.set_yticks(y)
        ax2a.set_yticklabels(ops, fontsize=9)
        ax2a.set_xlabel('Total selections by UCB')
        ax2a.set_title('Operator Selection Frequency\n(UCB learned preferences)')
        ax2a.grid(True, axis='x', alpha=0.3)

        # Success rate
        colors = ['green' if r > 10 else 'orange' if r > 5 else 'salmon' for r in success_rates]
        ax2b.barh(y, success_rates, color=colors, alpha=0.8)
        ax2b.set_yticks(y)
        ax2b.set_yticklabels(ops, fontsize=9)
        ax2b.set_xlabel('Success rate (%)')
        ax2b.set_title('Operator Success Rate\n(% of selections that passed tests & improved)')
        ax2b.grid(True, axis='x', alpha=0.3)
        ax2b.axvline(0, color='grey', linewidth=0.8)

        fig2.suptitle(f'UCB Operator Analysis — Exp 2 (timestamp {timestamp})',
                      fontsize=11, fontweight='bold')
        plt.tight_layout()

        if args.show:
            plt.show()
        else:
            out2 = BASE + f'/exp2_operator_analysis_{timestamp}.png'
            fig2.savefig(out2, dpi=150, bbox_inches='tight')
            print(f'Saved: {out2}')


if __name__ == '__main__':
    main()
