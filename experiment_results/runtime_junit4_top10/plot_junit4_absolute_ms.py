"""
JUnit4: Absolute runtime improvement (ms) — median + max per experiment.
Mirrors Wang et al. Fig. 3 style for direct comparison.

Experiments:
  Exp 1: Random Sampling       — 5 reps, timestamp 20260326_004421
  Exp 2: UCB + Traditional     — 5 reps, timestamp 20260325_213836
  Exp 3: UCB + All (Trad+LLM) — 3 reps, 7B model, timestamp 20260329_164655
  Exp 4: Standard LS + Trad   — 5 reps, timestamp 20260325_213836
  Exp 5: Standard LS + All    — 3 reps, 7B model, timestamp 20260329_164655

For each rep: per-method best absolute improvement (ms) = baseline_ms - best_patch_ms.
Then across reps: median and max.

Usage:
    python3 plot_junit4_absolute_ms.py
    python3 plot_junit4_absolute_ms.py --show
"""

import csv, glob, io, os, argparse
import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

EXP1_PATTERN = os.path.join(BASE, 'exp1_random_rep*_20260326_004421.csv')
EXP2_PATTERN = os.path.join(BASE, 'exp2_ucb_trad_rep*_20260325_213836.csv')
EXP3_PATTERN = os.path.join(BASE, 'exp3_ucb_all_7b_rep*_20260329_164655.csv')
EXP4_PATTERN = os.path.join(BASE, 'exp4_ls_trad_rep*_20260325_213836.csv')
EXP5_PATTERN = os.path.join(BASE, 'exp5_ls_all_7b_rep*_20260329_164655.csv')


def short_name(full_name):
    full_name = full_name.strip('"').strip()
    paren = full_name.find('(')
    if paren == -1:
        return full_name.split('.')[-1]
    prefix = full_name[:paren]
    parts = prefix.split('.')
    method = parts[-1]
    class_name = parts[-2] if len(parts) >= 2 else ''
    if method == 'runnerForClass':
        return f'{class_name}.{method}'
    return method


def load_exp1_abs(files):
    """RandomSampler CSVs: BaselineRuntime(ms) + PatchRuntime(ms) columns."""
    results = defaultdict(list)
    all_methods = set()
    for f in sorted(files):
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = short_name(row['MethodName'])
                all_methods.add(name)
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
        for m in method_baseline:
            bl = method_baseline[m]
            best = method_best_rt.get(m, bl)
            results[m].append(max(bl - best, 0.0))
    return results, sorted(all_methods)


def load_ls_abs(files):
    """RLLocalSearch / LocalSearch CSVs: Runtime(ms) or Fitness column, baseline at Iteration==-1."""
    results = defaultdict(list)
    all_methods = set()
    for f in sorted(files):
        method_baseline = {}
        method_best_rt = {}
        with open(f, newline='') as fh:
            lines = fh.readlines()
        # Keep header (first line containing MethodName) + data lines starting with '"'
        header = next((l for l in lines if 'MethodName' in l), lines[0])
        data_lines = [l for l in lines if l.startswith('"')]
        reader = csv.DictReader(io.StringIO(header + ''.join(data_lines)))
        for row in reader:
            try:
                name = short_name(row['MethodName'])
                iteration = int((row['Iteration'] or '').strip('"'))
                compiled = (row['Compiled'] or '').strip('"').strip().lower() == 'true'
                passed = (row['AllTestsPassed'] or '').strip('"').strip().lower() == 'true'
                rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                rt = float(rt_raw.strip('"'))
            except (ValueError, KeyError, TypeError):
                continue
            all_methods.add(name)
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
            best = method_best_rt.get(m, bl)
            results[m].append(max(bl - best, 0.0))
    return results, sorted(all_methods)


def stats(exp_data, method_order):
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

    exp1, methods1 = load_exp1_abs(sorted(glob.glob(EXP1_PATTERN)))
    exp2, methods2 = load_ls_abs(sorted(glob.glob(EXP2_PATTERN)))
    exp3, methods3 = load_ls_abs(sorted(glob.glob(EXP3_PATTERN)))
    exp4, methods4 = load_ls_abs(sorted(glob.glob(EXP4_PATTERN)))
    exp5, methods5 = load_ls_abs(sorted(glob.glob(EXP5_PATTERN)))

    all_methods = sorted(set(methods1 + methods2 + methods3 + methods4 + methods5))

    print(f'Files loaded: Exp1={len(glob.glob(EXP1_PATTERN))} reps, '
          f'Exp2={len(glob.glob(EXP2_PATTERN))}, Exp3={len(glob.glob(EXP3_PATTERN))}, '
          f'Exp4={len(glob.glob(EXP4_PATTERN))}, Exp5={len(glob.glob(EXP5_PATTERN))}')
    print(f'Methods found: {all_methods}\n')

    # Sort by Exp2 median descending
    method_order = sorted(all_methods,
                          key=lambda m: -np.median(exp2.get(m, [0.0])))

    # Print table
    print(f'{"Method":<38} {"E1 Rand":>12} {"E2 UCB":>12} {"E3 UCB+LLM":>12} {"E4 LS":>12} {"E5 LS+LLM":>12}')
    print('-' * 104)

    csv_lines = ['Method,E1_median_ms,E1_max_ms,E2_median_ms,E2_max_ms,E3_median_ms,E3_max_ms,'
                 'E4_median_ms,E4_max_ms,E5_median_ms,E5_max_ms']

    for m in method_order:
        vals = []
        for exp_data in [exp1, exp2, exp3, exp4, exp5]:
            rep_vals = exp_data.get(m, [0.0])
            med = np.median(rep_vals)
            mx = np.max(rep_vals)
            vals.append((med, mx))
        row_str = f'{m:<38}'
        for med, mx in vals:
            row_str += f'  {med:4.0f}/{mx:4.0f}ms'
        print(row_str)
        csv_lines.append(f'{m},' + ','.join(f'{med:.1f},{mx:.1f}' for med, mx in vals))

    print('-' * 104)

    # Totals
    print(f'{"TOTAL (sum medians)":<38}', end='')
    for exp_data in [exp1, exp2, exp3, exp4, exp5]:
        medians, maxes = stats(exp_data, method_order)
        print(f'  {sum(medians):4.0f}/{sum(maxes):4.0f}ms', end='')
    print('\n(med/max per cell)')

    # Save CSV
    csv_path = os.path.join(BASE, 'junit4_absolute_ms_summary.csv')
    with open(csv_path, 'w') as fh:
        fh.write('JUnit4: Absolute runtime improvement (ms) — median and max per experiment\n')
        fh.write('Exp3+Exp5 use 7B model (qwen2.5-coder), NPE-fixed run (timestamp 164655).\n\n')
        fh.write('\n'.join(csv_lines) + '\n')
    print(f'\nSaved: {csv_path}')

    # ---- Figure: Wang Fig. 3 style ----
    experiments = [
        ('Exp 1: Random', exp1, 'steelblue'),
        ('Exp 2: UCB+Trad', exp2, 'darkorange'),
        ('Exp 3: UCB+LLM (7B)', exp3, 'darkorchid'),
        ('Exp 4: LS+Trad', exp4, 'seagreen'),
        ('Exp 5: LS+LLM (7B)', exp5, 'teal'),
    ]

    fig, axes = plt.subplots(len(experiments), 1, figsize=(12, 3.2 * len(experiments)),
                              sharex=False)
    fig.suptitle('JUnit4: Absolute Runtime Improvement per Method (ms)\n'
                 'MAX (light) and MEDIAN (dark) across repetitions', fontsize=12, fontweight='bold')

    for ax, (label, exp_data, color) in zip(axes, experiments):
        medians, maxes = stats(exp_data, method_order)
        y = np.arange(len(method_order))

        ax.barh(y, maxes, height=0.5, color=color, alpha=0.4, label='MAX')
        ax.barh(y, medians, height=0.5, color=color, alpha=0.9, label='MEDIAN')

        ax.set_yticks(y)
        ax.set_yticklabels(method_order, fontsize=8)
        ax.set_xlabel('Runtime improvement (ms)')
        ax.set_title(label, fontsize=10, loc='left')
        ax.axvline(0, color='grey', linewidth=0.7)
        ax.grid(True, axis='x', alpha=0.3)
        ax.legend(fontsize=8, loc='lower right')

        for i, (med, mx) in enumerate(zip(medians, maxes)):
            if mx > 1:
                ax.text(mx + 0.5, i, f'{mx:.0f}', va='center', fontsize=7, color=color)

    plt.tight_layout()
    out = os.path.join(BASE, 'junit4_absolute_ms_wang_style.png')
    if args.show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


if __name__ == '__main__':
    main()
