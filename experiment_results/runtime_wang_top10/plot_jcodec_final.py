"""
jcodec: Final set of publication-quality graphs.

Figures generated:
  1. jcodec_final_wang_style.png       — Wang Fig.3-style per-method improvement (Exp1-4, 100 steps)
  2. jcodec_final_summary_totals.png   — Sum of median improvements per experiment (100-step)
  3. jcodec_final_500steps.png         — Exp2 vs Exp4 at 100 steps vs 500 steps
  4. jcodec_final_ucb_convergence.png  — Cumulative best improvement over search steps (Exp3 vs Exp4)
  5. jcodec_final_operator_freq.png    — Operator selection frequency + success rate (Exp3 RL log)

Canonical file sets (100-step):
  Exp1: exp1_random_rep*_20260312_143630.csv               (5 reps)
  Exp2: exp2_ucb_trad_rep*_20260312_143630.csv              (5 reps)
  Exp3: exp3_ucb_all_rep1_20260316_230008.csv  +
        exp3_ucb_all_rep{2,3}_20260330_001857.csv            (3 reps, borrowed baselines injected)
  Exp4: exp4_ls_trad_rep*_20260319_123900.csv               (5 reps)
  Exp5: EXCLUDED — only 3/10 methods complete, no 500-step run exists.

500-step files (Exp2+Exp4 only, separate folder):
  Exp2: ../runtime_wang_top10_500steps/exp2_ucb_trad_rep*_20260324_174223.csv
  Exp4: ../runtime_wang_top10_500steps/exp4_ls_trad_rep*_20260324_174223.csv

Usage:
    python3 plot_jcodec_final.py
    python3 plot_jcodec_final.py --show
"""

import csv, glob, io, os, argparse
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

BASE   = os.path.dirname(os.path.abspath(__file__))
BASE500 = os.path.join(BASE, '..', 'runtime_wang_top10_500steps')

# ── canonical file lists ──────────────────────────────────────────────────────
EXP1_FILES = sorted(glob.glob(os.path.join(BASE, 'exp1_random_rep*_20260312_143630.csv')))
EXP2_FILES = sorted(glob.glob(os.path.join(BASE, 'exp2_ucb_trad_rep*_20260312_143630.csv')))
EXP3_FILES = [
    os.path.join(BASE, 'exp3_ucb_all_rep1_20260316_230008.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep2_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep3_20260330_001857.csv'),
]
EXP4_FILES = sorted(glob.glob(os.path.join(BASE, 'exp4_ls_trad_rep*_20260319_123900.csv'))) + \
             [os.path.join(BASE, 'exp4_ls_trad_rep6_20260402_015048.csv')]

EXP2_500_FILES = sorted(glob.glob(os.path.join(BASE500, 'exp2_ucb_trad_rep*_20260324_174223.csv')))
EXP4_500_FILES = sorted(glob.glob(os.path.join(BASE500, 'exp4_ls_trad_rep*_20260324_174223.csv')))

EXP3_RL_FILES = [
    os.path.join(BASE, 'exp3_rl_log_rep1_20260316_230008.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep2_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep3_20260330_001857.csv'),
]

METHODS_ORDER = [
    'filterBs4', 'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert',
    'mergeResidual', 'resample', 'getPlaneWidth',
]

COLORS = {
    'exp1': 'steelblue',
    'exp2': 'darkorange',
    'exp3': 'darkorchid',
    'exp4': 'seagreen',
}


# ── helpers ───────────────────────────────────────────────────────────────────

def short_name(full_name):
    full_name = full_name.strip('"').strip()
    for key in sorted(METHODS_ORDER, key=len, reverse=True):  # longest first avoids filterBs matching filterBs4
        if key in full_name:
            return key
    return full_name.split('(')[0].split('.')[-1]


def load_exp1(files):
    """RandomSampler: BaselineRuntime(ms) + PatchRuntime(ms)."""
    results = defaultdict(list)
    for f in files:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            for row in csv.DictReader(fh):
                name = short_name(row['MethodName'])
                compiled = row['Compiled'].strip('"').lower() == 'true'
                passed   = row['AllTestsPassed'].strip('"').lower() == 'true'
                try:
                    bl = float(row['BaselineRuntime(ms)'].strip('"'))
                    pr = float(row['PatchRuntime(ms)'].strip('"'))
                except (ValueError, KeyError):
                    continue
                if bl > 0:
                    m_bl[name] = bl
                if compiled and passed and pr > 0:
                    if name not in m_best or pr < m_best[name]:
                        m_best[name] = pr
        for m in METHODS_ORDER:
            bl   = m_bl.get(m, 0)
            best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
    return results


def load_ls(files):
    """RLLocalSearch / LocalSearch CSVs (iteration-based).
    Returns (improvement_ms dict, baseline_ms dict) both keyed by method name."""
    results   = defaultdict(list)
    baselines = defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            try:
                name   = short_name(row['MethodName'])
                it     = int((row['Iteration'] or '').strip('"'))
                comp   = (row['Compiled'] or '').strip('"').lower() == 'true'
                passed = (row['AllTestsPassed'] or '').strip('"').lower() == 'true'
                rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                rt     = float(rt_raw.strip('"'))
            except (ValueError, KeyError, TypeError):
                continue
            if it == -1:
                if rt < 1e300:
                    m_bl[name] = rt
                continue
            if name not in m_bl:
                continue
            if comp and passed and 0 < rt < 1e300:
                if name not in m_best or rt < m_best[name]:
                    m_best[name] = rt
        for m in METHODS_ORDER:
            bl   = m_bl.get(m, 0)
            best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
            if bl > 0:
                baselines[m].append(bl)
    return results, baselines


def stats(exp_data):
    medians = [float(np.median(exp_data.get(m, [0.0]))) for m in METHODS_ORDER]
    maxes   = [float(np.max(exp_data.get(m, [0.0])))    for m in METHODS_ORDER]
    return medians, maxes


def pct_stats(exp_data, ref_baselines):
    """Per-method median improvement expressed as % of baseline.
    ref_baselines: dict {method: list_of_baseline_ms} — use median as reference."""
    medians_pct, maxes_pct = [], []
    for m in METHODS_ORDER:
        bl = float(np.median(ref_baselines.get(m, [1.0]))) or 1.0
        imp_vals = exp_data.get(m, [0.0])
        medians_pct.append(float(np.median(imp_vals)) / bl * 100)
        maxes_pct.append(float(np.max(imp_vals)) / bl * 100)
    return medians_pct, maxes_pct


# ── Figure 1: Wang-style per-method (Exp1-4, 100 steps) ──────────────────────

def fig_wang_style(exp1, exp2, exp3, exp4, show):
    experiments = [
        ('Exp 1: Random sampling (5 reps)', exp1, COLORS['exp1']),
        ('Exp 2: UCB + Traditional operators (5 reps)', exp2, COLORS['exp2']),
        ('Exp 3: UCB + All operators incl. LLM (3 reps)', exp3, COLORS['exp3']),
        ('Exp 4: Standard LS + Traditional operators (5 reps)', exp4, COLORS['exp4']),
    ]
    fig, axes = plt.subplots(4, 1, figsize=(12, 14), constrained_layout=True)
    fig.suptitle('jcodec: Absolute Runtime Improvement per Method (ms) — 100 steps\n'
                 'Bars show MEDIAN (solid) and MAX (light) across repetitions',
                 fontsize=12, fontweight='bold')

    for ax, (label, exp_data, color) in zip(axes, experiments):
        medians, maxes = stats(exp_data)
        y = np.arange(len(METHODS_ORDER))
        ax.barh(y, maxes,   height=0.55, color=color, alpha=0.30, label='MAX')
        ax.barh(y, medians, height=0.55, color=color, alpha=0.90, label='MEDIAN')
        ax.set_yticks(y)
        ax.set_yticklabels(METHODS_ORDER, fontsize=9)
        ax.set_xlabel('Runtime improvement (ms)')
        ax.set_title(label, fontsize=9, loc='left', pad=3)
        ax.axvline(0, color='grey', linewidth=0.7)
        ax.grid(True, axis='x', alpha=0.3)
        ax.legend(fontsize=8, loc='lower right')
        for i, (med, mx) in enumerate(zip(medians, maxes)):
            if mx > 5:
                ax.text(mx + 2, i, f'{mx:.0f}', va='center', fontsize=7, color=color)

    out = os.path.join(BASE, 'jcodec_final_wang_style.png')
    if show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


# ── Figure 2: Summary totals (percentage-based) ───────────────────────────────

def fig_summary_totals(exp1, exp2, exp3, exp4, ref_bl, show):
    labels = ['Exp 1\nRandom', 'Exp 2\nUCB+Trad', 'Exp 3\nUCB+LLM', 'Exp 4\nLS+Trad']
    colors = [COLORS['exp1'], COLORS['exp2'], COLORS['exp3'], COLORS['exp4']]
    exps   = [exp1, exp2, exp3, exp4]

    sum_pct_meds, sum_pct_maxs, per_method_pct_meds = [], [], []
    for exp_data in exps:
        meds_pct, maxs_pct = pct_stats(exp_data, ref_bl)
        sum_pct_meds.append(sum(meds_pct))
        sum_pct_maxs.append(sum(maxs_pct))
        per_method_pct_meds.append(meds_pct)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    fig.suptitle('jcodec: Runtime Improvement Summary — 100 steps (% of baseline)',
                 fontsize=12, fontweight='bold')

    # Left: sum of % medians
    x = np.arange(len(labels))
    bars = ax1.bar(x, sum_pct_meds, color=colors, alpha=0.85, width=0.5)
    ax1.bar(x, sum_pct_maxs, color=colors, alpha=0.25, width=0.5, label='Sum of MAXes')
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel('Sum of median % improvements across all methods')
    ax1.set_title('Total improvement (sum of per-method % over baseline)', fontsize=9)
    ax1.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, sum_pct_meds):
        ax1.text(bar.get_x() + bar.get_width()/2, val + 1, f'{val:.1f}%',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Right: grouped per-method % medians
    n_exp = len(exps)
    width = 0.18
    offsets = np.linspace(-(n_exp-1)*width/2, (n_exp-1)*width/2, n_exp)
    y = np.arange(len(METHODS_ORDER))
    for i, (meds_pct, color, label) in enumerate(zip(per_method_pct_meds, colors, labels)):
        ax2.barh(y + offsets[i], meds_pct, height=width, color=color, alpha=0.85,
                 label=label.replace('\n', ' '))
    ax2.set_yticks(y)
    ax2.set_yticklabels(METHODS_ORDER, fontsize=8)
    ax2.set_xlabel('Median improvement (% of baseline runtime)')
    ax2.set_title('Per-method improvement (%)', fontsize=9)
    ax2.legend(fontsize=8)
    ax2.grid(True, axis='x', alpha=0.3)
    ax2.axvline(0, color='grey', linewidth=0.7)

    out = os.path.join(BASE, 'jcodec_final_summary_totals.png')
    if show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


# ── Figure 3: 100 vs 500 steps (Exp2 + Exp4) — percentage-based ──────────────

def fig_500steps(exp2_100, exp4_100, exp2_500, exp4_500, ref_bl, show, ref_bl_100=None):
    if ref_bl_100 is None:
        ref_bl_100 = ref_bl
    meds_e2_100, _ = pct_stats(exp2_100, ref_bl_100)
    meds_e4_100, _ = pct_stats(exp4_100, ref_bl_100)
    meds_e2_500, _ = pct_stats(exp2_500, ref_bl)
    meds_e4_500, _ = pct_stats(exp4_500, ref_bl)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6), constrained_layout=True)
    fig.suptitle('jcodec: Effect of Search Budget — UCB (Exp 2) vs Standard LS (Exp 4)\n'
                 'Improvement shown as % of baseline runtime',
                 fontsize=12, fontweight='bold')

    # Left: per-method comparison (% medians)
    ax = axes[0]
    y  = np.arange(len(METHODS_ORDER))
    w  = 0.2
    ax.barh(y - 1.5*w, meds_e2_100, height=w, color=COLORS['exp2'], alpha=0.5,  label='Exp 2 UCB @ 100 steps')
    ax.barh(y - 0.5*w, meds_e2_500, height=w, color=COLORS['exp2'], alpha=0.95, label='Exp 2 UCB @ 500 steps')
    ax.barh(y + 0.5*w, meds_e4_100, height=w, color=COLORS['exp4'], alpha=0.5,  label='Exp 4 LS @ 100 steps')
    ax.barh(y + 1.5*w, meds_e4_500, height=w, color=COLORS['exp4'], alpha=0.95, label='Exp 4 LS @ 500 steps')
    ax.set_yticks(y)
    ax.set_yticklabels(METHODS_ORDER, fontsize=8)
    ax.set_xlabel('Median improvement (% of baseline runtime)')
    ax.set_title('Per-method median improvement (%)', fontsize=9)
    ax.axvline(0, color='grey', linewidth=0.7)
    ax.grid(True, axis='x', alpha=0.3)
    ax.legend(fontsize=8)

    # Right: total % bar chart
    ax2 = axes[1]
    labels_bar = ['UCB\n100 steps', 'UCB\n500 steps', 'LS\n100 steps', 'LS\n500 steps']
    totals     = [sum(meds_e2_100), sum(meds_e2_500), sum(meds_e4_100), sum(meds_e4_500)]
    bar_colors = [COLORS['exp2'], COLORS['exp2'], COLORS['exp4'], COLORS['exp4']]
    alphas     = [0.5, 0.95, 0.5, 0.95]
    x = np.arange(len(labels_bar))
    bars = [ax2.bar(x[i], totals[i], color=bar_colors[i], alpha=alphas[i], width=0.5)
            for i in range(len(totals))]
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels_bar, fontsize=9)
    ax2.set_ylabel('Sum of per-method median % improvements')
    ax2.set_title('Total improvement — sum of % gains across all 10 methods', fontsize=9)
    ax2.grid(True, axis='y', alpha=0.3)
    for b, val in zip([bar[0] for bar in bars], totals):
        ax2.text(b.get_x() + b.get_width()/2, val + 1, f'{val:.1f}%',
                 ha='center', va='bottom', fontsize=9, fontweight='bold')

    # annotation: UCB overtakes LS at 500 steps
    if sum(meds_e2_500) > sum(meds_e4_500):
        ax2.annotate('UCB overtakes LS\nat 500 steps',
                     xy=(1, sum(meds_e2_500)), xytext=(1.6, sum(meds_e2_500) * 0.85),
                     fontsize=8, arrowprops=dict(arrowstyle='->', color='grey'), color='grey')

    out = os.path.join(BASE, 'jcodec_final_500steps.png')
    if show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


# ── Figure 4: Convergence — cumulative best improvement over steps ────────────

def load_cumulative_best_from_ls(files, n_steps=100):
    """
    From main LS CSVs: for each method, track best runtime at each iteration.
    Returns dict {method: array[n_steps+1]} where index 0 = baseline.
    Averaged across reps.
    """
    method_curves = defaultdict(list)
    for f in files:
        lines = open(f).readlines()
        header = next((l for l in lines if 'MethodName' in l), lines[0])
        data   = [l for l in lines if l.startswith('"')]
        m_bl, m_by_step = {}, defaultdict(dict)
        for row in csv.DictReader(io.StringIO(header + ''.join(data))):
            try:
                name = short_name(row['MethodName'])
                it   = int((row['Iteration'] or '').strip('"'))
                comp = (row['Compiled'] or '').strip('"').lower() == 'true'
                passed = (row['AllTestsPassed'] or '').strip('"').lower() == 'true'
                rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                rt = float(rt_raw.strip('"'))
            except (ValueError, KeyError, TypeError):
                continue
            if it == -1:
                if rt < 1e300:
                    m_bl[name] = rt
            elif comp and passed and 0 < rt < 1e300:
                m_by_step[name][it] = min(m_by_step[name].get(it, rt), rt)
        for m in METHODS_ORDER:
            if m not in m_bl:
                continue
            bl = m_bl[m]
            curve = np.zeros(n_steps + 1)
            best_so_far = bl
            for step in range(1, n_steps + 1):
                if step in m_by_step[m]:
                    best_so_far = min(best_so_far, m_by_step[m][step])
                curve[step] = max(bl - best_so_far, 0.0)
            method_curves[m].append(curve)
    # average across reps
    avg = {}
    for m in METHODS_ORDER:
        curves = method_curves[m]
        if curves:
            avg[m] = np.mean(curves, axis=0)
    return avg


def load_cumulative_best_from_rllog(files, main_files, n_steps=100):
    """
    From RL log CSVs: for each MethodID, track cumulative best ChildRuntime.
    MethodID→name mapping comes from the main exp3 CSV (order of first appearance).
    Returns dict {method: array[n_steps+1]} averaged across reps.
    """
    # Build MethodID → name from first main file
    method_id_map = {}
    lines = open(main_files[0]).readlines()
    header = next((l for l in lines if 'MethodName' in l), lines[0])
    data   = [l for l in lines if l.startswith('"')]
    seen_order = []
    for row in csv.DictReader(io.StringIO(header + ''.join(data))):
        try:
            it = int(row['Iteration'].strip('"'))
        except: continue
        if it == -1:
            name = short_name(row['MethodName'])
            if name not in seen_order:
                seen_order.append(name)
    for i, name in enumerate(seen_order, start=1):
        method_id_map[i] = name

    # Get baselines from main files
    m_baselines = defaultdict(list)
    for f in main_files:
        lines = open(f).readlines()
        header = next((l for l in lines if 'MethodName' in l), lines[0])
        data   = [l for l in lines if l.startswith('"')]
        for row in csv.DictReader(io.StringIO(header + ''.join(data))):
            try:
                it  = int(row['Iteration'].strip('"'))
                rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                rt  = float(rt_raw.strip('"'))
            except: continue
            if it == -1 and rt < 1e300:
                name = short_name(row['MethodName'])
                m_baselines[name].append(rt)
    baseline_med = {m: float(np.median(v)) for m, v in m_baselines.items() if v}

    method_curves = defaultdict(list)
    for f in files:
        if not os.path.exists(f):
            continue
        m_by_step = defaultdict(dict)
        with open(f, newline='') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    mid  = int(row['MethodID'])
                    step = int(row['Step'])
                    child_rt = float(row['ChildRuntime(ms)'])
                    success  = row['Success'].strip().lower() == 'true'
                except (ValueError, KeyError):
                    continue
                if success and child_rt > 0:
                    m_by_step[mid][step] = min(m_by_step[mid].get(step, child_rt), child_rt)
        for mid, name in method_id_map.items():
            if name not in baseline_med:
                continue
            bl = baseline_med[name]
            curve = np.zeros(n_steps + 1)
            best_so_far = bl
            for step in range(1, n_steps + 1):
                if step in m_by_step[mid]:
                    best_so_far = min(best_so_far, m_by_step[mid][step])
                curve[step] = max(bl - best_so_far, 0.0)
            method_curves[name].append(curve)

    avg = {}
    for m in METHODS_ORDER:
        curves = method_curves[m]
        if curves:
            avg[m] = np.mean(curves, axis=0)
    return avg


def fig_convergence(exp3_curves, exp4_curves, show):
    """Plot aggregate (sum across methods) cumulative best improvement vs step."""
    steps = np.arange(101)

    def aggregate(curves):
        total = np.zeros(101)
        for m in METHODS_ORDER:
            if m in curves:
                total += curves[m]
        return total

    e3_total = aggregate(exp3_curves)
    e4_total = aggregate(exp4_curves)

    # also compute per-method for the lower panel
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9), constrained_layout=True)
    fig.suptitle('jcodec: Search Convergence — Cumulative Best Runtime Improvement vs Step',
                 fontsize=12, fontweight='bold')

    # Top: aggregate
    ax1.plot(steps, e3_total, color=COLORS['exp3'], lw=2.0,
             label='Exp 3: UCB + All (incl. LLM) — avg across 3 reps')
    ax1.plot(steps, e4_total, color=COLORS['exp4'], lw=2.0, ls='--',
             label='Exp 4: Standard LS + Trad — avg across 5 reps')
    ax1.fill_between(steps, e3_total, e4_total,
                     where=e3_total >= e4_total, alpha=0.12, color=COLORS['exp3'],
                     label='Exp 3 ahead')
    ax1.fill_between(steps, e4_total, e3_total,
                     where=e4_total > e3_total, alpha=0.12, color=COLORS['exp4'],
                     label='Exp 4 ahead')
    ax1.set_xlabel('Search step (per method)')
    ax1.set_ylabel('Sum of best improvement across methods (ms)')
    ax1.set_title('Aggregate improvement across all 10 methods', fontsize=9)
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 100)

    # Bottom: heatmap-style — one row per method, colour = improvement at final step
    n = len(METHODS_ORDER)
    final_e3 = [exp3_curves[m][-1] if m in exp3_curves else 0 for m in METHODS_ORDER]
    final_e4 = [exp4_curves[m][-1] if m in exp4_curves else 0 for m in METHODS_ORDER]
    x = np.arange(n)
    w = 0.35
    ax2.barh(x - w/2, final_e3, height=w, color=COLORS['exp3'], alpha=0.85,
             label='Exp 3 UCB+LLM final improvement')
    ax2.barh(x + w/2, final_e4, height=w, color=COLORS['exp4'], alpha=0.85,
             label='Exp 4 LS+Trad final improvement')
    ax2.set_yticks(x)
    ax2.set_yticklabels(METHODS_ORDER, fontsize=8)
    ax2.set_xlabel('Average best improvement at step 100 (ms)')
    ax2.set_title('Per-method improvement at end of search', fontsize=9)
    ax2.legend(fontsize=9)
    ax2.grid(True, axis='x', alpha=0.3)
    ax2.axvline(0, color='grey', lw=0.7)

    out = os.path.join(BASE, 'jcodec_final_ucb_convergence.png')
    if show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


# ── Figure 5: Operator selection frequency + success rate (Exp3 RL log) ───────

def fig_operator_freq(rl_files, show):
    op_counts   = defaultdict(int)
    op_success  = defaultdict(int)

    for f in rl_files:
        if not os.path.exists(f):
            continue
        with open(f, newline='') as fh:
            for row in csv.DictReader(fh):
                try:
                    op      = row['Operator'].strip()
                    success = row['Success'].strip().lower() == 'true'
                except KeyError:
                    continue
                op_counts[op]  += 1
                if success:
                    op_success[op] += 1

    if not op_counts:
        print('No RL log data found — skipping operator freq plot.')
        return

    ops      = sorted(op_counts, key=lambda o: -op_counts[o])
    counts   = [op_counts[o] for o in ops]
    rates    = [op_success[o] / op_counts[o] * 100 for o in ops]

    # Shorten operator names
    def shorten(name):
        return (name.replace('Statement', 'Stmt')
                    .replace('Matched', 'M.')
                    .replace('Replace', 'Rep.')
                    .replace('LLM', 'LLM-')
                    .replace('Masked', 'Masked'))

    ops_short = [shorten(o) for o in ops]
    trad_mask = ['LLM' not in o for o in ops]

    colors = [COLORS['exp2'] if t else COLORS['exp3'] for t in trad_mask]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle('jcodec Exp 3: UCB Operator Selection — aggregated over 3 reps × 10 methods',
                 fontsize=12, fontweight='bold')

    y = np.arange(len(ops))
    ax1.barh(y, counts, color=colors, alpha=0.85)
    ax1.set_yticks(y)
    ax1.set_yticklabels(ops_short, fontsize=8)
    ax1.set_xlabel('Total times selected by UCB')
    ax1.set_title('Selection frequency', fontsize=9)
    trad_patch = mpatches.Patch(color=COLORS['exp2'], alpha=0.85, label='Traditional')
    llm_patch  = mpatches.Patch(color=COLORS['exp3'], alpha=0.85, label='LLM')
    ax1.legend(handles=[trad_patch, llm_patch], fontsize=9)
    ax1.grid(True, axis='x', alpha=0.3)
    for i, v in enumerate(counts):
        ax1.text(v + 0.5, i, str(v), va='center', fontsize=7)

    ax2.barh(y, rates, color=colors, alpha=0.85)
    ax2.set_yticks(y)
    ax2.set_yticklabels(ops_short, fontsize=8)
    ax2.set_xlabel('Success rate (%)')
    ax2.set_title('Success rate (compiled + all tests passed)', fontsize=9)
    ax2.legend(handles=[trad_patch, llm_patch], fontsize=9)
    ax2.grid(True, axis='x', alpha=0.3)
    for i, v in enumerate(rates):
        ax2.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=7)
    ax2.set_xlim(0, max(rates) * 1.2)

    out = os.path.join(BASE, 'jcodec_final_operator_freq.png')
    if show:
        plt.show()
    else:
        fig.savefig(out, dpi=150, bbox_inches='tight')
        print(f'Saved: {out}')
    plt.close(fig)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    print('Loading experiment data...')
    print(f'  Exp1: {len(EXP1_FILES)} files')
    print(f'  Exp2: {len(EXP2_FILES)} files')
    print(f'  Exp3: {len([f for f in EXP3_FILES if os.path.exists(f)])} files (canonical 3)')
    print(f'  Exp4: {len(EXP4_FILES)} files')
    print(f'  Exp2@500: {len(EXP2_500_FILES)} files')
    print(f'  Exp4@500: {len(EXP4_500_FILES)} files')

    exp1 = load_exp1(EXP1_FILES)
    exp2_100, bl2    = load_ls(EXP2_FILES)
    exp3_100, bl3    = load_ls([f for f in EXP3_FILES if os.path.exists(f)])
    exp4_100, bl4    = load_ls(EXP4_FILES)
    exp2_500, bl2_500 = load_ls(EXP2_500_FILES)
    exp4_500, bl4_500 = load_ls(EXP4_500_FILES)

    # Reference baseline for 100-step experiments: pool Exp2+Exp3+Exp4 (100-step only)
    all_bls_100 = defaultdict(list)
    for d in [bl2, bl3, bl4]:
        for m, vals in d.items():
            all_bls_100[m].extend(vals)
    ref_bl_100 = {m: np.median(v) for m, v in all_bls_100.items() if v}

    # Reference baselines for 500-step figures: pool all sources
    all_bls = defaultdict(list)
    for d in [bl2, bl3, bl4, bl2_500, bl4_500]:
        for m, vals in d.items():
            all_bls[m].extend(vals)
    ref_bl = {m: np.median(v) for m, v in all_bls.items() if v}

    # Print summary table (ms and %)
    print(f'\n{"Method":<24} {"BL(ms)":>7} | {"E1 ms/%":>11} {"E2 ms/%":>11} {"E3 ms/%":>11} {"E4 ms/%":>11}')
    print('-' * 85)
    for m in METHODS_ORDER:
        bl = ref_bl.get(m, 1.0)
        row = f'{m:<24} {bl:7.0f} |'
        for exp_data in [exp1, exp2_100, exp3_100, exp4_100]:
            vals = exp_data.get(m, [0.0])
            med = float(np.median(vals))
            pct = med / bl * 100
            row += f'  {med:5.0f}/{pct:4.1f}%'
        print(row)
    print('-' * 85)
    print(f'{"Sum med ms / sum %":<24} {"":>7} |', end='')
    for exp_data in [exp1, exp2_100, exp3_100, exp4_100]:
        meds, _ = stats(exp_data)
        meds_pct, _ = pct_stats(exp_data, ref_bl)
        print(f'  {sum(meds):5.0f}/{sum(meds_pct):4.1f}%', end='')
    print('\n')

    print('Generating figures...')

    print('  Fig 1: Wang-style per-method comparison (ms)...')
    fig_wang_style(exp1, exp2_100, exp3_100, exp4_100, args.show)

    print('  Fig 2: Summary totals (%)...')
    fig_summary_totals(exp1, exp2_100, exp3_100, exp4_100, ref_bl_100, args.show)

    print('  Fig 3: 100 vs 500 steps (Exp2 + Exp4, %)...')
    fig_500steps(exp2_100, exp4_100, exp2_500, exp4_500, ref_bl, args.show, ref_bl_100=ref_bl_100)

    print('  Fig 4: Convergence curves...')
    exp3_curves = load_cumulative_best_from_rllog(
        [f for f in EXP3_RL_FILES if os.path.exists(f)],
        [f for f in EXP3_FILES if os.path.exists(f)]
    )
    exp4_curves = load_cumulative_best_from_ls(EXP4_FILES)
    fig_convergence(exp3_curves, exp4_curves, args.show)

    print('  Fig 5: Operator selection frequency...')
    fig_operator_freq([f for f in EXP3_RL_FILES if os.path.exists(f)], args.show)

    print('\nAll done.')


if __name__ == '__main__':
    main()
