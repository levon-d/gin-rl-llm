"""
jcodec: Absolute runtime improvement (ms) — median + max per experiment.
Mirrors Wang et al. Fig. 3 style for direct comparison.

Experiments:
  Exp 1: Random Sampling       — 5 reps, timestamp 20260312_143630  (pn=100, note limitation)
  Exp 2: UCB + Traditional     — 5 reps, timestamp 20260312_143630
  Exp 3: UCB + All (Trad+LLM) — 4 reps, timestamp 20260316_230008
  Exp 4: Standard LS + Trad   — 5 reps, timestamp 20260319_123900
  Exp 5: Standard LS + All    — 2 reps, timestamp 20260323_140041

For each rep: per-method best absolute improvement (ms) = baseline_ms - best_patch_ms.
Then across reps: median and max.

Usage:
    python3 plot_jcodec_absolute_ms.py
    python3 plot_jcodec_absolute_ms.py --show
"""

import csv, glob, os, argparse  # glob used in EXP1/2/4 file lists
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

EXP1_FILES = sorted(glob.glob(os.path.join(BASE, 'exp1_random_rep*_20260312_143630.csv')))
EXP2_FILES = sorted(glob.glob(os.path.join(BASE, 'exp2_ucb_trad_rep*_20260312_143630.csv')))
EXP3_FILES = [
    os.path.join(BASE, 'exp3_ucb_all_rep1_20260316_230008.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep2_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep3_20260330_001857.csv'),
]
EXP4_FILES = sorted(glob.glob(os.path.join(BASE, 'exp4_ls_trad_rep*_20260319_123900.csv'))) + \
             [os.path.join(BASE, 'exp4_ls_trad_rep6_20260402_015048.csv')]
EXP5_FILES = [
    os.path.join(BASE, 'exp5_ls_all_rep1_20260331_152947.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep2_20260331_152947.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep3_20260401_141651.csv'),
]

METHODS_ORDER = [
    'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'filterBs4',
    'mergeResidual', 'resample', 'getPlaneWidth',
]


def short_name(full_name):
    full_name = full_name.strip('"').strip()
    for key in sorted(METHODS_ORDER, key=len, reverse=True):
        if key in full_name:
            return key
    return full_name.split('.')[-1]


def load_exp1_abs(files):
    """RandomSampler CSVs: BaselineRuntime(ms) + PatchRuntime(ms) columns."""
    results = defaultdict(list)
    for f in sorted(files):
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = short_name(row['MethodName'])
                compiled = row['Compiled'].strip('"').strip().lower() == 'true'
                passed = row['AllTestsPassed'].strip('"').strip().lower() == 'true'
                try:
                    baseline = float(row['BaselineRuntime(ms)'].strip('"'))
                    patch_rt = float(row['PatchRuntime(ms)'].strip('"'))
                except (ValueError, KeyError):
                    continue
                if baseline > 0:
                    method_baseline[name] = baseline
                if compiled and passed and patch_rt > 0:
                    if name not in method_best_rt or patch_rt < method_best_rt[name]:
                        method_best_rt[name] = patch_rt
        for m in METHODS_ORDER:
            bl = method_baseline.get(m, 0)
            best = method_best_rt.get(m, bl)
            improvement_ms = max(bl - best, 0.0) if bl > 0 else 0.0
            results[m].append(improvement_ms)
    return results


def load_ls_abs(files):
    """RLLocalSearch / LocalSearch CSVs: Runtime(ms) or Fitness column, baseline at Iteration==-1."""
    results = defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            try:
                name = short_name(row['MethodName'])
                iteration = int((row['Iteration'] or '').strip('"'))
                compiled = (row['Compiled'] or '').strip('"').strip().lower() == 'true'
                passed = (row['AllTestsPassed'] or '').strip('"').strip().lower() == 'true'
                rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                rt = float(rt_raw.strip('"'))
            except (ValueError, KeyError, TypeError):
                continue
            if iteration == -1:
                if rt < 1e300:
                    method_baseline[name] = rt
                continue
            if name not in method_baseline:
                continue
            if compiled and passed and 0 < rt < 1e300:
                if name not in method_best_rt or rt < method_best_rt[name]:
                    method_best_rt[name] = rt
        for m in METHODS_ORDER:
            bl = method_baseline.get(m, 0)
            best = method_best_rt.get(m, bl)
            improvement_ms = max(bl - best, 0.0) if bl > 0 else 0.0
            results[m].append(improvement_ms)
    return results


def stats(exp_data, method_order):
    """Returns (medians, maxes) lists aligned to method_order."""
    medians, maxes = [], []
    for m in method_order:
        vals = exp_data.get(m, [0.0])
        medians.append(float(np.median(vals)))
        maxes.append(float(np.max(vals)))
    return medians, maxes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    exp1 = load_exp1_abs(EXP1_FILES)
    exp2 = load_ls_abs(EXP2_FILES)
    exp3 = load_ls_abs(EXP3_FILES)
    exp4 = load_ls_abs(EXP4_FILES)
    exp5 = load_ls_abs(EXP5_FILES)

    print(f'Files loaded: Exp1={len(EXP1_FILES)} reps, Exp2={len(EXP2_FILES)}, '
          f'Exp3={len([f for f in EXP3_FILES if os.path.exists(f)])}, '
          f'Exp4={len(EXP4_FILES)}, Exp5={len([f for f in EXP5_FILES if os.path.exists(f)])}')
    print('NOTE: Exp5 completed only 5-6 of 10 methods; remaining show 0 improvement.\n')

    # Print table
    header = f'{"Method":<28} {"E1 Rand":>12} {"E2 UCB":>12} {"E3 UCB+LLM":>12} {"E4 LS":>12} {"E5 LS+LLM":>12}'
    print(header)
    print('-' * len(header))

    csv_lines = ['Method,E1_median_ms,E1_max_ms,E2_median_ms,E2_max_ms,E3_median_ms,E3_max_ms,'
                 'E4_median_ms,E4_max_ms,E5_median_ms,E5_max_ms']

    total_row = []
    for exp_data in [exp1, exp2, exp3, exp4, exp5]:
        medians, _ = stats(exp_data, METHODS_ORDER)
        total_row.append((np.median(medians), np.max(medians)))

    for m in METHODS_ORDER:
        vals = []
        for exp_data in [exp1, exp2, exp3, exp4, exp5]:
            rep_vals = exp_data.get(m, [0.0])
            med = np.median(rep_vals)
            mx = np.max(rep_vals)
            vals.append((med, mx))
        row_str = f'{m:<28}'
        for med, mx in vals:
            row_str += f'  {med:4.0f}/{mx:4.0f}ms'
        print(row_str)
        csv_lines.append(f'{m},' + ','.join(f'{med:.1f},{mx:.1f}' for med, mx in vals))

    print('-' * len(header))
    print('(med/max per cell)\n')

    # Summary totals (sum of medians across methods, max of maxes)
    print(f'{"TOTAL (sum medians)":<28}', end='')
    for exp_data in [exp1, exp2, exp3, exp4, exp5]:
        medians, maxes = stats(exp_data, METHODS_ORDER)
        print(f'  {sum(medians):4.0f}/{sum(maxes):4.0f}ms', end='')
    print()

    # Save CSV
    csv_path = os.path.join(BASE, 'jcodec_absolute_ms_summary.csv')
    with open(csv_path, 'w') as fh:
        fh.write('jcodec: Absolute runtime improvement (ms) — median and max per experiment\n')
        fh.write('NOTE: Exp1 pn=100 (undersampled). Exp3=4 reps, Exp5=2 reps, others=5 reps.\n\n')
        fh.write('\n'.join(csv_lines) + '\n')
    print(f'\nSaved: {csv_path}')

    # ---- Figure: Wang Fig. 3 style — max + median per experiment per method ----
    experiments = [
        ('Exp 1\nRandom (pn=100)', exp1, 'steelblue'),
        ('Exp 2\nUCB+Trad', exp2, 'darkorange'),
        ('Exp 3\nUCB+LLM', exp3, 'darkorchid'),
        ('Exp 4\nLS+Trad', exp4, 'seagreen'),
        ('Exp 5\nLS+LLM', exp5, 'teal'),
    ]

    fig, axes = plt.subplots(len(experiments), 1, figsize=(12, 3.2 * len(experiments)),
                              sharex=False)
    fig.suptitle('jcodec: Absolute Runtime Improvement per Method (ms)\n'
                 'MAX (dark) and MEDIAN (light) across repetitions', fontsize=12, fontweight='bold')

    for ax, (label, exp_data, color) in zip(axes, experiments):
        medians, maxes = stats(exp_data, METHODS_ORDER)
        y = np.arange(len(METHODS_ORDER))

        ax.barh(y, maxes, height=0.5, color=color, alpha=0.4, label='MAX')
        ax.barh(y, medians, height=0.5, color=color, alpha=0.9, label='MEDIAN')

        ax.set_yticks(y)
        ax.set_yticklabels(METHODS_ORDER, fontsize=8)
        ax.set_xlabel('Runtime improvement (ms)')
        ax.set_title(label, fontsize=10, loc='left')
        ax.axvline(0, color='grey', linewidth=0.7)
        ax.grid(True, axis='x', alpha=0.3)
        ax.legend(fontsize=8, loc='lower right')

        # Annotate max values
        for i, (med, mx) in enumerate(zip(medians, maxes)):
            if mx > 1:
                ax.text(mx + 1, i, f'{mx:.0f}', va='center', fontsize=7, color=color)

    plt.tight_layout()
    out = os.path.join(BASE, 'jcodec_absolute_ms_wang_style.png')
    if args.show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


if __name__ == '__main__':
    main()
