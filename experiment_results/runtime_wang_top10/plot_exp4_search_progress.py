"""
Plot Standard Local Search (Exp 4) search progress.

For each method (5x2 grid), shows best runtime improvement found so far at each step,
one line per repetition plus a bold dashed mean line.

CSV columns: MethodName, Iteration, EvaluationNumber, Patch, Compiled, AllTestsPassed,
             TotalExecutionTime(ms), Fitness, FitnessImprovement
Baseline row: Iteration == "-1"; steps start at "1".
Runtime (ms) == Fitness column (index 7).

Usage:
    python3 plot_exp4_search_progress.py
    python3 plot_exp4_search_progress.py --timestamp 20260319_123900
    python3 plot_exp4_search_progress.py --show
"""

import csv, os, glob, argparse
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

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


def load_exp4_rep(filepath):
    """
    Parse one Exp4 rep file.
    Returns:
        baselines: dict  short -> baseline runtime (ms)
        steps:     dict  short -> list of (step_num, runtime_ms)  — only valid passing rows
                         (runtime < 1e300)
        all_steps: dict  short -> list of step_nums in order (including failing ones, for x-axis)
    """
    baselines = {}
    steps = defaultdict(list)      # short -> [(step, runtime)]
    all_steps = defaultdict(list)  # short -> [step, ...]

    with open(filepath, newline='') as fh:
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
                try:
                    step_num = int(iteration)
                except ValueError:
                    continue
                all_steps[short].append(step_num)
                if passed and fitness < 1e300:
                    steps[short].append((step_num, fitness))

    return baselines, steps, all_steps


def compute_best_so_far(baselines, steps, all_steps, short):
    """
    Returns (xs, pct_improvements) arrays tracking best-so-far improvement% at each step.
    """
    baseline = baselines.get(short, None)
    if baseline is None or baseline <= 0:
        return np.array([]), np.array([])

    # Build fast lookup: step -> best runtime at that step (only passing)
    step_rt = {}
    for step, rt in steps.get(short, []):
        if step not in step_rt or rt < step_rt[step]:
            step_rt[step] = rt

    sorted_steps = sorted(all_steps.get(short, []))
    if not sorted_steps:
        return np.array([]), np.array([])

    best_so_far = baseline
    xs = []
    ys = []
    for s in sorted_steps:
        if s in step_rt and step_rt[s] < best_so_far:
            best_so_far = step_rt[s]
        pct = 100.0 * (baseline - best_so_far) / baseline
        xs.append(s)
        ys.append(pct)

    return np.array(xs), np.array(ys)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timestamp', default=None,
                        help='Exp4 timestamp, e.g. 20260319_123900. Auto-detected if omitted.')
    parser.add_argument('--show', action='store_true',
                        help='Show plot interactively instead of saving.')
    args = parser.parse_args()

    # Auto-detect timestamp
    if args.timestamp:
        timestamp = args.timestamp
    else:
        files = sorted(
            f for f in glob.glob(BASE + '/exp4_ls_trad_rep1_*.csv')
            if 'summary' not in f
        )
        if not files:
            print('No exp4_ls_trad_rep1_*.csv found.')
            return
        timestamp = '_'.join(os.path.basename(files[-1]).replace('.csv', '').split('_')[-2:])
    print(f'Using timestamp: {timestamp}')

    # Load all reps
    rep_files = sorted(glob.glob(BASE + f'/exp4_ls_trad_rep*_{timestamp}.csv'))
    print(f'Found {len(rep_files)} rep files.')

    all_reps = {}  # rep_num -> (baselines, steps, all_steps)
    for filepath in rep_files:
        basename = os.path.basename(filepath)
        rep_num = int(basename.split('_rep')[1].split('_')[0])
        all_reps[rep_num] = load_exp4_rep(filepath)

    if not all_reps:
        print('No rep data loaded. Exiting.')
        return

    n_methods = len(METHODS_ORDER)
    n_cols = 2
    n_rows = (n_methods + n_cols - 1) // n_cols  # = 5

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, n_rows * 3.5))
    axes = axes.flatten()

    colors = cm.tab10(np.linspace(0, 0.9, len(all_reps)))

    for ax_idx, short in enumerate(METHODS_ORDER):
        ax = axes[ax_idx]
        all_ys = []
        all_xs = []

        for rep_idx, (rep_num, (baselines, steps, all_steps)) in enumerate(
            sorted(all_reps.items())
        ):
            xs, ys = compute_best_so_far(baselines, steps, all_steps, short)
            if xs.size == 0:
                continue

            ax.plot(xs, ys, color=colors[rep_idx], alpha=0.6,
                    linewidth=1.2, label=f'Rep {rep_num}')
            all_ys.append(ys)
            all_xs.append(xs)

        # Mean line
        if len(all_ys) > 1:
            min_len = min(len(y) for y in all_ys)
            mean_y = np.mean([y[:min_len] for y in all_ys], axis=0)
            ref_xs = all_xs[0][:min_len]
            ax.plot(ref_xs, mean_y, color='black',
                    linewidth=2.0, linestyle='--', label='Mean')
        elif len(all_ys) == 1:
            ax.plot(all_xs[0], all_ys[0], color='black',
                    linewidth=2.0, linestyle='--', label='Mean')

        ax.set_title(short, fontsize=10, fontweight='bold')
        ax.set_xlabel('Step')
        ax.set_ylabel('Best improvement (%)')
        ax.axhline(0, color='grey', linewidth=0.8, linestyle=':')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    # Hide unused subplots (if n_methods is odd)
    for i in range(n_methods, len(axes)):
        axes[i].set_visible(False)

    fig.suptitle(
        f'Standard Local Search Progress \u2014 Best Runtime Improvement per Step\n'
        f'(Exp 4, {len(all_reps)} reps, timestamp {timestamp})',
        fontsize=12, fontweight='bold'
    )
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out = BASE + f'/exp4_search_progress_{timestamp}.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')


if __name__ == '__main__':
    main()
