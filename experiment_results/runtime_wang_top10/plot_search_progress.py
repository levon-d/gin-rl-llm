"""
Plot UCB search progress for Experiment 2.

For each method, shows how the best runtime found so far improves
as the number of steps increases — one line per repetition, plus a mean line.

Usage:
    python3 plot_search_progress.py
    python3 plot_search_progress.py --timestamp 20260308_004051
    python3 plot_search_progress.py --show   # display instead of saving
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

def short_name(method_id, id_to_name):
    name = id_to_name.get(int(method_id), '')
    for key in METHODS_ORDER:
        if key.rstrip('(') in name:
            return key
    return name


def load_rl_log(filepath):
    """
    Returns dict: method_id -> list of (step, child_runtime, reward)
    Skips failed evaluations (ChildRuntime == -1).
    """
    data = defaultdict(list)
    with open(filepath) as f:
        reader = csv.reader(f)
        next(reader)  # header
        for row in reader:
            method_id = int(row[0])
            step = int(row[1])
            success = row[3].strip().lower() == 'true'
            parent_rt = float(row[4])
            child_rt = float(row[5])
            data[method_id].append((step, success, parent_rt, child_rt))
    return data


def best_so_far(steps_data, baseline):
    """Given a list of (step, success, parent_rt, child_rt), return
    arrays of step numbers and best runtime found so far at each step."""
    best = baseline
    xs, ys = [], []
    for step, success, parent_rt, child_rt in steps_data:
        if success and child_rt > 0 and child_rt < best:
            best = child_rt
        xs.append(step)
        ys.append(best)
    return np.array(xs), np.array(ys)


def load_runtime_summary(filepath):
    """Returns dict: short_name -> baseline runtime (ms)"""
    baselines = {}
    with open(filepath) as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            name = row[0].strip('"')
            if name == 'TOTAL':
                continue
            for key in METHODS_ORDER:
                if key.rstrip('(') in name:
                    baselines[key] = float(row[1])
                    break
    return baselines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timestamp', default=None,
                        help='Timestamp suffix, e.g. 20260308_004051. Defaults to latest.')
    parser.add_argument('--show', action='store_true',
                        help='Show plots interactively instead of saving.')
    args = parser.parse_args()

    # Find RL log files
    pattern = BASE + '/exp2_rl_log_rep*'
    if args.timestamp:
        pattern += '_' + args.timestamp + '.csv'
    else:
        pattern += '_*.csv'

    rl_files = sorted(f for f in glob.glob(pattern)
                      if 'summary' not in os.path.basename(f)
                      and 'runtime' not in os.path.basename(f))

    if not rl_files:
        print('No RL log files found matching pattern:', pattern)
        return

    # Infer timestamp from filenames
    timestamps = set()
    for f in rl_files:
        base_name = os.path.basename(f)
        # exp2_rl_log_repN_TIMESTAMP.csv
        parts = base_name.replace('.csv', '').split('_')
        ts = '_'.join(parts[-2:])
        timestamps.add(ts)
    timestamp = sorted(timestamps)[-1]  # use latest if multiple
    print(f'Using timestamp: {timestamp}')
    print(f'Found {len(rl_files)} rep files.')

    # Load baselines from rep1 runtime summary
    summary_file = BASE + f'/exp2_rl_log_rep1_{timestamp}_runtime_summary.csv'
    baselines = load_runtime_summary(summary_file)

    # Load all reps
    all_reps = {}  # rep_num -> {method_id -> [(step, success, parent_rt, child_rt)]}
    method_id_to_name = {}

    for filepath in rl_files:
        base_name = os.path.basename(filepath)
        rep_num = int(base_name.split('_rep')[1].split('_')[0])
        all_reps[rep_num] = load_rl_log(filepath)

    # Get method IDs and map to short names via summary
    rep1_data = list(all_reps.values())[0]
    method_ids = sorted(rep1_data.keys())

    # Build id -> short name from summary file
    id_to_short = {}
    with open(summary_file) as f:
        reader = csv.reader(f)
        next(reader)
        for i, row in enumerate(reader):
            name = row[0].strip('"')
            if name == 'TOTAL':
                continue
            for key in METHODS_ORDER:
                if key.rstrip('(') in name:
                    id_to_short[method_ids[i] if i < len(method_ids) else i+1] = key
                    break

    # If mapping failed, use positional
    if not id_to_short:
        for i, mid in enumerate(method_ids):
            id_to_short[mid] = METHODS_ORDER[i] if i < len(METHODS_ORDER) else str(mid)

    n_methods = len(method_ids)
    n_cols = 2
    n_rows = (n_methods + 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(14, n_rows * 3.5))
    axes = axes.flatten()

    colors = cm.tab10(np.linspace(0, 0.9, len(all_reps)))

    for ax_idx, method_id in enumerate(method_ids):
        ax = axes[ax_idx]
        short = id_to_short.get(method_id, str(method_id))
        baseline = baselines.get(short, None)

        all_ys = []

        for rep_idx, (rep_num, rep_data) in enumerate(sorted(all_reps.items())):
            steps_data = rep_data.get(method_id, [])
            if not steps_data:
                continue

            # Use baseline from summary if available, else first parent_rt
            bl = baseline if baseline else steps_data[0][2]
            xs, ys = best_so_far(steps_data, bl)
            pct_improvement = 100.0 * (bl - ys) / bl

            ax.plot(xs, pct_improvement, color=colors[rep_idx],
                    alpha=0.6, linewidth=1.2, label=f'Rep {rep_num}')
            all_ys.append(pct_improvement)

        # Mean line across reps
        if all_ys and len(all_ys) > 1:
            min_len = min(len(y) for y in all_ys)
            mean_y = np.mean([y[:min_len] for y in all_ys], axis=0)
            ax.plot(range(1, min_len + 1), mean_y, color='black',
                    linewidth=2, linestyle='--', label='Mean')

        ax.set_title(short, fontsize=10, fontweight='bold')
        ax.set_xlabel('Step')
        ax.set_ylabel('Best improvement (%)')
        ax.axhline(0, color='grey', linewidth=0.8, linestyle=':')
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3)

    # Hide unused subplots
    for i in range(n_methods, len(axes)):
        axes[i].set_visible(False)

    fig.suptitle(f'UCB Search Progress — Best Runtime Improvement per Step\n(Exp 2, {len(all_reps)} reps, timestamp {timestamp})',
                 fontsize=12, fontweight='bold')
    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out = BASE + f'/exp2_search_progress_{timestamp}.png'
        plt.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')


if __name__ == '__main__':
    main()
