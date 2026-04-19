"""
Plot Exp 1 vs Exp 2 vs Exp 4 comparison (grouped bar chart).

Exp 1: Random Sampling  (steelblue)
Exp 2: UCB Local Search (darkorange)
Exp 4: Standard Local Search (seagreen)

Produces two figures:
  1. Grouped bar chart: mean improvement % per method (3 bars each)
  2. Horizontal bar chart: TOTAL mean improvement per experiment

Usage:
    python3 plot_exp4_comparison.py
    python3 plot_exp4_comparison.py --timestamp 20260319_123900
    python3 plot_exp4_comparison.py --show
"""

import csv, os, glob, argparse
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

EXP1_TIMESTAMP = '20260316_124805'
EXP2_TIMESTAMP = '20260312_143630'

METHODS_ORDER = [
    'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'filterBs4',
    'mergeResidual', 'resample', 'getPlaneWidth',
]

METHODS_KEYS = [
    ('filterBs(', 'filterBs'),
    ('estimateQPix', 'estimateQPix'),
    ('takeSafe', 'takeSafe'),
    ('getLumaPred4x4', 'getLumaPred4x4'),
    ('filterBlockEdgeHoris', 'filterBlockEdgeHoris'),
    ('filterBlockEdgeVert', 'filterBlockEdgeVert'),
    ('filterBs4', 'filterBs4'),
    ('mergeResidual', 'mergeResidual'),
    ('resample', 'resample'),
    ('getPlaneWidth', 'getPlaneWidth'),
]


def short_name(method):
    for key, short in METHODS_KEYS:
        if key in method:
            return short
    return method


def load_exp1_best(timestamp):
    """Returns dict: short -> list of improvement% per rep."""
    results = defaultdict(list)
    files = sorted(
        f for f in glob.glob(BASE + f'/exp1_random_rep*_{timestamp}.csv')
        if 'summary' not in f
    )
    for f in files:
        method_best = {}
        method_baseline = {}
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                passed = row['AllTestsPassed'].strip().lower() == 'true'
                meth = row['MethodName'].strip()
                short = short_name(meth)
                baseline = float(row['BaselineRuntime(ms)'])
                patch_rt = float(row['PatchRuntime(ms)'])
                method_baseline[short] = baseline
                if passed and patch_rt > 0 and patch_rt < baseline:
                    if short not in method_best or patch_rt < method_best[short]:
                        method_best[short] = patch_rt
        for _, short in METHODS_KEYS:
            bl = method_baseline.get(short, 0)
            best = method_best.get(short, bl)
            pct = 100.0 * (bl - best) / bl if bl > 0 else 0.0
            results[short].append(pct)
    return results


def load_exp2_best(timestamp):
    """Returns dict: short -> list of improvement% per rep (from runtime_summary CSVs)."""
    results = defaultdict(list)
    files = sorted(glob.glob(BASE + f'/exp2_rl_log_rep*_{timestamp}_runtime_summary.csv'))
    for f in files:
        with open(f, newline='') as fh:
            reader = csv.reader(fh)
            next(reader)  # header
            for row in reader:
                name = row[0].strip('"')
                if name == 'TOTAL':
                    continue
                short = short_name(name)
                results[short].append(float(row[4]))
    return results


def load_exp4_best(timestamp):
    """Returns dict: short -> list of improvement% per rep (from raw Exp4 CSVs)."""
    results = defaultdict(list)
    files = sorted(glob.glob(BASE + f'/exp4_ls_trad_rep*_{timestamp}.csv'))
    for f in files:
        baselines = {}
        bests = {}
        with open(f, newline='') as fh:
            reader = csv.reader(fh)
            next(reader)  # header
            for row in reader:
                if len(row) < 8:
                    continue
                method_full = row[0].strip()
                iteration = row[1].strip()
                passed = row[5].strip().lower() == 'true'
                try:
                    fitness = float(row[7])
                except ValueError:
                    continue
                short = short_name(method_full)
                if iteration == '-1':
                    baselines[short] = fitness
                else:
                    if passed and fitness < 1e300:
                        if short not in bests or fitness < bests[short]:
                            bests[short] = fitness
        for _, short in METHODS_KEYS:
            bl = baselines.get(short, 0.0)
            best = bests.get(short, bl)
            pct = 100.0 * (bl - best) / bl if bl > 0 else 0.0
            results[short].append(pct)
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timestamp', default=None,
                        help='Exp4 timestamp, e.g. 20260319_123900. Auto-detected if omitted.')
    parser.add_argument('--show', action='store_true',
                        help='Show plots interactively instead of saving.')
    args = parser.parse_args()

    # Auto-detect Exp4 timestamp
    if args.timestamp:
        exp4_ts = args.timestamp
    else:
        files = sorted(
            f for f in glob.glob(BASE + '/exp4_ls_trad_rep1_*.csv')
            if 'summary' not in f
        )
        if not files:
            print('No exp4_ls_trad_rep1_*.csv found.')
            return
        exp4_ts = '_'.join(os.path.basename(files[-1]).replace('.csv', '').split('_')[-2:])
    print(f'Exp1 timestamp: {EXP1_TIMESTAMP}')
    print(f'Exp2 timestamp: {EXP2_TIMESTAMP}')
    print(f'Exp4 timestamp: {exp4_ts}')

    exp1 = load_exp1_best(EXP1_TIMESTAMP)
    exp2 = load_exp2_best(EXP2_TIMESTAMP)
    exp4 = load_exp4_best(exp4_ts)

    # ---- Figure 1: Grouped bar chart per method ----
    fig1, ax1 = plt.subplots(figsize=(14, 5))

    x = np.arange(len(METHODS_ORDER))
    width = 0.25

    e1_means = [np.mean(exp1.get(m, [0])) for m in METHODS_ORDER]
    e1_stds  = [np.std(exp1.get(m, [0]))  for m in METHODS_ORDER]
    e2_means = [np.mean(exp2.get(m, [0])) for m in METHODS_ORDER]
    e2_stds  = [np.std(exp2.get(m, [0]))  for m in METHODS_ORDER]
    e4_means = [np.mean(exp4.get(m, [0])) for m in METHODS_ORDER]
    e4_stds  = [np.std(exp4.get(m, [0]))  for m in METHODS_ORDER]

    ax1.bar(x - width, e1_means, width, yerr=e1_stds,
            label='Exp 1: Random Sampling', color='steelblue', alpha=0.85, capsize=4)
    ax1.bar(x,         e2_means, width, yerr=e2_stds,
            label='Exp 2: UCB Local Search', color='darkorange', alpha=0.85, capsize=4)
    ax1.bar(x + width, e4_means, width, yerr=e4_stds,
            label='Exp 4: Standard Local Search', color='seagreen', alpha=0.85, capsize=4)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Mean improvement over baseline (%)')
    ax1.set_title(
        'Best Improvement Found per Method: Random vs UCB vs Standard Local Search\n'
        '(mean \u00b1 std across 5 repetitions)'
    )
    ax1.set_xticks(x)
    ax1.set_xticklabels(METHODS_ORDER, rotation=30, ha='right', fontsize=9)
    ax1.legend(fontsize=9)
    ax1.axhline(0, color='grey', linewidth=0.8, linestyle=':')
    ax1.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out1 = BASE + f'/exp1_exp2_exp4_comparison_{exp4_ts}.png'
        fig1.savefig(out1, dpi=150, bbox_inches='tight')
        print(f'Saved: {out1}')

    # ---- Figure 2: Horizontal bar — TOTAL mean improvement per experiment ----
    def total_mean(data):
        all_pcts = []
        for _, short in METHODS_KEYS:
            vals = data.get(short, [0])
            all_pcts.append(np.mean(vals))
        return np.mean(all_pcts)

    fig2, ax2 = plt.subplots(figsize=(7, 4))

    labels = ['Exp 1: Random\nSampling', 'Exp 2: UCB\nLocal Search', 'Exp 4: Standard\nLocal Search']
    means  = [total_mean(exp1), total_mean(exp2), total_mean(exp4)]
    colors = ['steelblue', 'darkorange', 'seagreen']

    y = np.arange(len(labels))
    bars = ax2.barh(y, means, color=colors, alpha=0.85, height=0.5)

    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel('Mean improvement over baseline (%)')
    ax2.set_title('Total Mean Improvement per Experiment\n(averaged across methods and repetitions)')
    ax2.axvline(0, color='grey', linewidth=0.8)
    ax2.grid(True, axis='x', alpha=0.3)

    for bar, val in zip(bars, means):
        ax2.text(max(val + 0.02, 0.02), bar.get_y() + bar.get_height() / 2,
                 f'{val:.2f}%', va='center', fontsize=10)

    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out2 = BASE + f'/exp1_exp2_exp4_total_summary_{exp4_ts}.png'
        fig2.savefig(out2, dpi=150, bbox_inches='tight')
        print(f'Saved: {out2}')


if __name__ == '__main__':
    main()
