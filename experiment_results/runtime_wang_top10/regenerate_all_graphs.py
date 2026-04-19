"""
Regenerate all 8 dissertation graphs with updated canonical file sets:
  Exp3: 5 reps  (reps 4+5 added 2026-04-08)
  Exp5: 5 reps  (reps 4+5 with calibrated -pb 0.8, added 2026-04-09)

Outputs:
  jcodec_absolute_ms_wang_style.png
  jcodec_final_operator_freq.png
  jcodec_final_summary_totals.png
  jcodec_final_ucb_convergence.png
  jcodec_final_wang_style.png
  metric1_heatmap.png
  metric1_per_method.png
  metric1_summary.png

Usage:
    python3 regenerate_all_graphs.py
"""

import csv, glob, io, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))
BASE500 = os.path.join(BASE, '..', 'runtime_wang_top10_500steps')

# ── Canonical file sets ───────────────────────────────────────────────────────

EXP1_FILES = sorted(glob.glob(os.path.join(BASE, 'exp1_random_rep*_20260312_143630.csv')))
EXP2_FILES = sorted(glob.glob(os.path.join(BASE, 'exp2_ucb_trad_rep*_20260312_143630.csv')))
EXP3_FILES = [
    os.path.join(BASE, 'exp3_ucb_all_rep1_20260316_230008.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep2_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep3_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep4_20260408_201948.csv'),
    os.path.join(BASE, 'exp3_ucb_all_rep5_20260408_201948.csv'),
]
EXP4_FILES = sorted(glob.glob(os.path.join(BASE, 'exp4_ls_trad_rep*_20260319_123900.csv'))) + \
             [os.path.join(BASE, 'exp4_ls_trad_rep6_20260402_015048.csv')]
EXP5_FILES = [
    os.path.join(BASE, 'exp5_ls_all_rep1_20260323_140041.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep2_20260331_152947.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep3_20260401_141651.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep4_cal_pb08_20260409_212652.csv'),
    os.path.join(BASE, 'exp5_ls_all_rep5_cal_pb08_20260409_151823.csv'),
]
EXP3_RL_FILES = [
    os.path.join(BASE, 'exp3_rl_log_rep1_20260316_230008.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep2_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep3_20260330_001857.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep4_20260408_201948.csv'),
    os.path.join(BASE, 'exp3_rl_log_rep5_20260408_201948.csv'),
]
EXP2_500_FILES = sorted(glob.glob(os.path.join(BASE500, 'exp2_ucb_trad_rep*_20260324_174223.csv')))
EXP4_500_FILES = sorted(glob.glob(os.path.join(BASE500, 'exp4_ls_trad_rep*_20260324_174223.csv')))

METHODS_ORDER = [
    'filterBs4', 'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'mergeResidual', 'resample', 'getPlaneWidth',
]

COLORS = {
    'exp1': 'steelblue',
    'exp2': 'darkorange',
    'exp3': 'darkorchid',
    'exp4': 'seagreen',
    'exp5': 'crimson',
}

EXP_LABELS = {
    'exp1': 'Exp 1: Random sampling',
    'exp2': 'Exp 2: UCB + Traditional ops',
    'exp3': 'Exp 3: UCB + All ops (incl. LLM)',
    'exp4': 'Exp 4: Standard LS + Traditional ops',
    'exp5': 'Exp 5: Standard LS + All ops (incl. LLM)',
}

REP_COUNTS = {'exp1': 5, 'exp2': 5, 'exp3': 5, 'exp4': 6, 'exp5': 5}


# ── Helpers ───────────────────────────────────────────────────────────────────

def short_name(full_name):
    full_name = full_name.strip('"').strip()
    for key in sorted(METHODS_ORDER, key=len, reverse=True):
        if key in full_name:
            return key
    return full_name.split('(')[0].split('.')[-1]


def load_exp1(files):
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


def imp_stats(exp_data):
    medians = [float(np.median(exp_data.get(m, [0.0]))) for m in METHODS_ORDER]
    maxes   = [float(np.max(exp_data.get(m, [0.0])))    for m in METHODS_ORDER]
    return medians, maxes


def pct_stats(exp_data, ref_bl):
    meds, maxs = [], []
    for m in METHODS_ORDER:
        bl = float(np.median(ref_bl.get(m, [1.0]))) or 1.0
        imp = exp_data.get(m, [0.0])
        meds.append(float(np.median(imp)) / bl * 100)
        maxs.append(float(np.max(imp))    / bl * 100)
    return meds, maxs


def metric_b_per_rep(files):
    """Returns list of per-rep mean(best_rt/baseline_rt*100) values."""
    rep_means = []
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            for row in csv.DictReader(fh):
                try:
                    name   = short_name(row['MethodName'])
                    it     = int((row['Iteration'] or '').strip('"'))
                    comp   = (row['Compiled'] or '').strip('"').lower() == 'true'
                    passed = (row['AllTestsPassed'] or '').strip('"').lower() == 'true'
                    rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                    rt     = float(rt_raw.strip('"'))
                except (ValueError, KeyError, TypeError):
                    continue
                if it == -1 and rt < 1e300:
                    m_bl[name] = rt
                elif it >= 0 and comp and passed and 0 < rt < 1e300:
                    if name not in m_best or rt < m_best[name]:
                        m_best[name] = rt
        ratios = [m_best.get(m, m_bl[m]) / m_bl[m] * 100
                  for m in METHODS_ORDER if m in m_bl]
        if ratios:
            rep_means.append(float(np.mean(ratios)))
    return rep_means


def metric_b_per_method(files):
    """Returns dict method -> list of per-rep (best_rt/baseline_rt*100)."""
    m_ratios = defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            for row in csv.DictReader(fh):
                try:
                    name   = short_name(row['MethodName'])
                    it     = int((row['Iteration'] or '').strip('"'))
                    comp   = (row['Compiled'] or '').strip('"').lower() == 'true'
                    passed = (row['AllTestsPassed'] or '').strip('"').lower() == 'true'
                    rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                    rt     = float(rt_raw.strip('"'))
                except (ValueError, KeyError, TypeError):
                    continue
                if it == -1 and rt < 1e300:
                    m_bl[name] = rt
                elif it >= 0 and comp and passed and 0 < rt < 1e300:
                    if name not in m_best or rt < m_best[name]:
                        m_best[name] = rt
        for m in METHODS_ORDER:
            if m in m_bl:
                m_ratios[m].append(m_best.get(m, m_bl[m]) / m_bl[m] * 100)
    return m_ratios


# ── Load all data ─────────────────────────────────────────────────────────────

print('Loading data...')
exp1             = load_exp1(EXP1_FILES)
exp2, bl2        = load_ls(EXP2_FILES)
exp3, bl3        = load_ls(EXP3_FILES)
exp4, bl4        = load_ls(EXP4_FILES)
exp5, bl5        = load_ls(EXP5_FILES)
exp2_500, bl2_500 = load_ls(EXP2_500_FILES)
exp4_500, bl4_500 = load_ls(EXP4_500_FILES)

# Pooled reference baseline: Exp2 + Exp3 + Exp4 (100-step only)
all_bls = defaultdict(list)
for d in [bl2, bl3, bl4]:
    for m, vals in d.items():
        all_bls[m].extend(vals)
ref_bl = {m: float(np.median(v)) for m, v in all_bls.items() if v}

print(f'  Exp1: {len(EXP1_FILES)} reps, Exp2: {len(EXP2_FILES)} reps, '
      f'Exp3: {len([f for f in EXP3_FILES if os.path.exists(f)])} reps, '
      f'Exp4: {len([f for f in EXP4_FILES if os.path.exists(f)])} reps, '
      f'Exp5: {len([f for f in EXP5_FILES if os.path.exists(f)])} reps')


# ── 1. jcodec_absolute_ms_wang_style.png ─────────────────────────────────────

print('Generating jcodec_absolute_ms_wang_style.png ...')

experiments = [
    (f'{EXP_LABELS["exp1"]} ({REP_COUNTS["exp1"]} reps)', exp1, COLORS['exp1']),
    (f'{EXP_LABELS["exp2"]} ({REP_COUNTS["exp2"]} reps)', exp2, COLORS['exp2']),
    (f'{EXP_LABELS["exp3"]} ({REP_COUNTS["exp3"]} reps)', exp3, COLORS['exp3']),
    (f'{EXP_LABELS["exp4"]} ({REP_COUNTS["exp4"]} reps)', exp4, COLORS['exp4']),
    (f'{EXP_LABELS["exp5"]} ({REP_COUNTS["exp5"]} reps)', exp5, COLORS['exp5']),
]

fig, axes = plt.subplots(5, 1, figsize=(12, 17), constrained_layout=True)
fig.suptitle('jcodec: Absolute Runtime Improvement per Method (ms) — 100 steps\n'
             'Bars show MEDIAN (solid) and MAX (light) across repetitions',
             fontsize=12, fontweight='bold')

for ax, (label, exp_data, color) in zip(axes, experiments):
    medians, maxes = imp_stats(exp_data)
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

fig.savefig(os.path.join(BASE, 'jcodec_absolute_ms_wang_style.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 2. jcodec_final_wang_style.png ───────────────────────────────────────────

print('Generating jcodec_final_wang_style.png ...')

fig, axes = plt.subplots(5, 1, figsize=(12, 17), constrained_layout=True)
fig.suptitle('jcodec: Runtime Improvement per Method (% of reference baseline) — 100 steps\n'
             'Bars show MEDIAN (solid) and MAX (light) across repetitions',
             fontsize=12, fontweight='bold')

for ax, (label, exp_data, color) in zip(axes, experiments):
    meds_pct, maxs_pct = pct_stats(exp_data, ref_bl)
    y = np.arange(len(METHODS_ORDER))
    ax.barh(y, maxs_pct,  height=0.55, color=color, alpha=0.30, label='MAX')
    ax.barh(y, meds_pct,  height=0.55, color=color, alpha=0.90, label='MEDIAN')
    ax.set_yticks(y)
    ax.set_yticklabels(METHODS_ORDER, fontsize=9)
    ax.set_xlabel('Improvement (% of reference baseline runtime)')
    ax.set_title(label, fontsize=9, loc='left', pad=3)
    ax.axvline(0, color='grey', linewidth=0.7)
    ax.grid(True, axis='x', alpha=0.3)
    ax.legend(fontsize=8, loc='lower right')
    for i, (med, mx) in enumerate(zip(meds_pct, maxs_pct)):
        if mx > 2:
            ax.text(mx + 0.3, i, f'{mx:.1f}%', va='center', fontsize=7, color=color)

fig.savefig(os.path.join(BASE, 'jcodec_final_wang_style.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 3. jcodec_final_summary_totals.png ───────────────────────────────────────

print('Generating jcodec_final_summary_totals.png ...')

exp_keys  = ['exp1', 'exp2', 'exp3', 'exp4', 'exp5']
all_exps  = [exp1, exp2, exp3, exp4, exp5]
bar_labels = ['Exp 1\nRandom', 'Exp 2\nUCB+Trad', 'Exp 3\nUCB+LLM', 'Exp 4\nLS+Trad', 'Exp 5\nLS+LLM']
colors     = [COLORS[k] for k in exp_keys]

sum_meds, sum_maxs, per_method_meds = [], [], []
for e in all_exps:
    meds, maxs = pct_stats(e, ref_bl)
    sum_meds.append(sum(meds))
    sum_maxs.append(sum(maxs))
    per_method_meds.append(meds)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
fig.suptitle('jcodec: Runtime Improvement Summary — All Experiments (100 steps)',
             fontsize=12, fontweight='bold')

x = np.arange(len(bar_labels))
ax1.bar(x, sum_maxs, color=colors, alpha=0.25, width=0.55)
bars = ax1.bar(x, sum_meds, color=colors, alpha=0.90, width=0.55)
ax1.set_xticks(x)
ax1.set_xticklabels(bar_labels, fontsize=9)
ax1.set_ylabel('Sum of % improvements across all 10 methods')
ax1.set_title('Total improvement (sum of per-method median % over baseline)', fontsize=9)
ax1.grid(True, axis='y', alpha=0.3)
for bar, val in zip(bars, sum_meds):
    ax1.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
             f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

# Arrow annotation for the shaded extension
exp3_idx  = 2
exp3_max  = sum_maxs[exp3_idx]
exp3_med  = sum_meds[exp3_idx]
mid_shade = (exp3_med + exp3_max) / 2
ax1.annotate('Best single-rep\nimprovement\n(upper bound)',
             xy=(exp3_idx, mid_shade),
             xytext=(exp3_idx + 0.7, mid_shade * 0.85),
             fontsize=8, ha='left', va='center',
             arrowprops=dict(arrowstyle='->', color='#555555', lw=1.2,
                             connectionstyle='arc3,rad=-0.15'),
             color='#444444')

n_exp   = len(all_exps)
bar_h   = 0.14
offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_h
ym      = np.arange(len(METHODS_ORDER))
right_labels = ['Exp 1: Random', 'Exp 2: UCB+Trad', 'Exp 3: UCB+LLM', 'Exp 4: LS+Trad', 'Exp 5: LS+LLM']
for meds, offset, color, lbl in zip(per_method_meds, offsets, colors, right_labels):
    ax2.barh(ym + offset, meds, height=bar_h, color=color, alpha=0.88, label=lbl)
ax2.set_yticks(ym)
ax2.set_yticklabels(METHODS_ORDER, fontsize=8)
ax2.set_xlabel('Median improvement (% of reference baseline runtime)')
ax2.set_title('Per-method improvement — median across repetitions', fontsize=9)
ax2.legend(fontsize=8, loc='lower right')
ax2.grid(True, axis='x', alpha=0.3)
ax2.axvline(0, color='grey', linewidth=0.7)

fig.savefig(os.path.join(BASE, 'jcodec_final_summary_totals.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 4. jcodec_final_operator_freq.png ────────────────────────────────────────

print('Generating jcodec_final_operator_freq.png ...')

op_counts, op_success = defaultdict(int), defaultdict(int)
LLM_OPS = {'LLMMaskedStatement', 'LLMReplaceStatement'}

for f in [f for f in EXP3_RL_FILES if os.path.exists(f)]:
    with open(f, newline='') as fh:
        for row in csv.DictReader(fh):
            try:
                op      = row['Operator'].strip()
                success = row['Success'].strip().lower() == 'true'
            except KeyError:
                continue
            op_counts[op] += 1
            if success:
                op_success[op] += 1

if op_counts:
    ops    = sorted(op_counts, key=lambda o: -op_counts[o])
    counts = [op_counts[o] for o in ops]
    rates  = [op_success[o] / op_counts[o] * 100 for o in ops]

    def shorten(name):
        return (name.replace('Statement', 'Stmt').replace('Matched', 'M.')
                    .replace('Replace', 'Rep.').replace('LLM', 'LLM-')
                    .replace('Masked', 'Masked'))

    ops_short = [shorten(o) for o in ops]
    is_trad   = ['LLM' not in o for o in ops]
    bar_colors = [COLORS['exp2'] if t else COLORS['exp3'] for t in is_trad]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle(f'jcodec Exp 3: UCB Operator Selection — aggregated over '
                 f'{len([f for f in EXP3_RL_FILES if os.path.exists(f)])} reps × 10 methods',
                 fontsize=12, fontweight='bold')

    y = np.arange(len(ops))
    ax1.barh(y, counts, color=bar_colors, alpha=0.85)
    ax1.set_yticks(y); ax1.set_yticklabels(ops_short, fontsize=8)
    ax1.set_xlabel('Total times selected by UCB')
    ax1.set_title('Selection frequency', fontsize=9)
    trad_patch = mpatches.Patch(color=COLORS['exp2'], alpha=0.85, label='Traditional')
    llm_patch  = mpatches.Patch(color=COLORS['exp3'], alpha=0.85, label='LLM')
    ax1.legend(handles=[trad_patch, llm_patch], fontsize=9)
    ax1.grid(True, axis='x', alpha=0.3)
    for i, v in enumerate(counts):
        ax1.text(v + 0.5, i, str(v), va='center', fontsize=7)

    ax2.barh(y, rates, color=bar_colors, alpha=0.85)
    ax2.set_yticks(y); ax2.set_yticklabels(ops_short, fontsize=8)
    ax2.set_xlabel('Success rate (%)')
    ax2.set_title('Success rate (compiled + all tests passed)', fontsize=9)
    ax2.legend(handles=[trad_patch, llm_patch], fontsize=9)
    ax2.grid(True, axis='x', alpha=0.3)
    for i, v in enumerate(rates):
        ax2.text(v + 0.3, i, f'{v:.1f}%', va='center', fontsize=7)
    ax2.set_xlim(0, max(rates) * 1.2 if rates else 10)

    fig.savefig(os.path.join(BASE, 'jcodec_final_operator_freq.png'), dpi=150, bbox_inches='tight')
    plt.close(fig)
    print('  Saved.')
else:
    print('  No RL log data — skipping.')


# ── 5. jcodec_final_ucb_convergence.png ──────────────────────────────────────

print('Generating jcodec_final_ucb_convergence.png ...')

def load_cumulative_from_ls(files, n_steps=100):
    method_curves = defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        lines  = open(f).readlines()
        header = next((l for l in lines if 'MethodName' in l), lines[0])
        data   = [l for l in lines if l.startswith('"')]
        m_bl, m_by_step = {}, defaultdict(dict)
        for row in csv.DictReader(io.StringIO(header + ''.join(data))):
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
            elif comp and passed and 0 < rt < 1e300:
                m_by_step[name][it] = min(m_by_step[name].get(it, rt), rt)
        for m in METHODS_ORDER:
            if m not in m_bl:
                continue
            bl   = m_bl[m]
            curve = np.zeros(n_steps + 1)
            best  = bl
            for step in range(1, n_steps + 1):
                if step in m_by_step[m]:
                    best = min(best, m_by_step[m][step])
                curve[step] = max(bl - best, 0.0)
            method_curves[m].append(curve)
    avg = {}
    for m in METHODS_ORDER:
        if method_curves[m]:
            avg[m] = np.mean(method_curves[m], axis=0)
    return avg

exp3_curves = load_cumulative_from_ls(EXP3_FILES)
exp4_curves = load_cumulative_from_ls(EXP4_FILES)

steps = np.arange(101)

def aggregate(curves):
    total = np.zeros(101)
    for m in METHODS_ORDER:
        if m in curves:
            total += curves[m]
    return total

e3_total = aggregate(exp3_curves)
e4_total = aggregate(exp4_curves)

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9), constrained_layout=True)
fig.suptitle('jcodec: Search Convergence — Cumulative Best Runtime Improvement vs Step',
             fontsize=12, fontweight='bold')

ax1.plot(steps, e3_total, color=COLORS['exp3'], lw=2.0,
         label=f'Exp 3: UCB + All ops (avg across {len([f for f in EXP3_FILES if os.path.exists(f)])} reps)')
ax1.plot(steps, e4_total, color=COLORS['exp4'], lw=2.0, ls='--',
         label=f'Exp 4: Standard LS + Trad (avg across {len([f for f in EXP4_FILES if os.path.exists(f)])} reps)')
ax1.fill_between(steps, e3_total, e4_total,
                 where=e3_total >= e4_total, alpha=0.12, color=COLORS['exp3'], label='Exp 3 ahead')
ax1.fill_between(steps, e4_total, e3_total,
                 where=e4_total > e3_total, alpha=0.12, color=COLORS['exp4'], label='Exp 4 ahead')
ax1.set_xlabel('Search step (per method)')
ax1.set_ylabel('Sum of best improvement across methods (ms)')
ax1.set_title('Aggregate improvement across all 10 methods', fontsize=9)
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_xlim(0, 100)

n = len(METHODS_ORDER)
final_e3 = [exp3_curves[m][-1] if m in exp3_curves else 0 for m in METHODS_ORDER]
final_e4 = [exp4_curves[m][-1] if m in exp4_curves else 0 for m in METHODS_ORDER]
diff     = [e3 - e4 for e3, e4 in zip(final_e3, final_e4)]
bar_colors_heat = [COLORS['exp3'] if d >= 0 else COLORS['exp4'] for d in diff]

y = np.arange(n)
ax2.barh(y, diff, color=bar_colors_heat, alpha=0.80)
ax2.set_yticks(y)
ax2.set_yticklabels(METHODS_ORDER, fontsize=8)
ax2.axvline(0, color='grey', linewidth=1.0)
ax2.set_xlabel('Final improvement difference: Exp 3 − Exp 4 (ms)')
ax2.set_title('Per-method: who wins at step 100? (positive = Exp 3 better)', fontsize=9)
ax2.grid(True, axis='x', alpha=0.3)
e3_patch = mpatches.Patch(color=COLORS['exp3'], alpha=0.8, label='Exp 3 better')
e4_patch = mpatches.Patch(color=COLORS['exp4'], alpha=0.8, label='Exp 4 better')
ax2.legend(handles=[e3_patch, e4_patch], fontsize=9)

fig.savefig(os.path.join(BASE, 'jcodec_final_ucb_convergence.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 6. metric1_heatmap.png — Metric B heatmap ────────────────────────────────

print('Generating metric1_heatmap.png ...')

all_exp_files = [EXP1_FILES, EXP2_FILES, EXP3_FILES, EXP4_FILES, EXP5_FILES]
col_labels    = ['Random\n+Trad', 'UCB\n+Trad', 'UCB\n+LLM', 'LS\n+Trad', 'LS\n+LLM']

# Build matrix: methods × experiments, value = median(best_rt/baseline*100)
heatmap_data = np.zeros((len(METHODS_ORDER), len(all_exp_files)))
for col_i, files in enumerate(all_exp_files):
    mb = metric_b_per_method(files)
    for row_i, m in enumerate(METHODS_ORDER):
        vals = mb.get(m, [100.0])
        heatmap_data[row_i, col_i] = float(np.median(vals)) if vals else 100.0

fig, ax = plt.subplots(figsize=(9, 6), constrained_layout=True)
fig.suptitle('Metric B Heatmap: Best Patch Runtime as % of Original\n'
             'Green = more improvement — lower is better',
             fontsize=11, fontweight='bold')

vmin, vmax = 70, 102
im = ax.imshow(heatmap_data, aspect='auto', cmap='RdYlGn_r', vmin=vmin, vmax=vmax)
ax.set_xticks(np.arange(len(col_labels)))
ax.set_xticklabels(col_labels, fontsize=9)
ax.set_yticks(np.arange(len(METHODS_ORDER)))
ax.set_yticklabels(METHODS_ORDER, fontsize=9)
ax.set_xlabel('Experiment')
ax.set_ylabel('% of original runtime')

for row_i in range(len(METHODS_ORDER)):
    for col_i in range(len(all_exp_files)):
        val = heatmap_data[row_i, col_i]
        text_color = 'white' if (val < 80 or val > 98) else 'black'
        ax.text(col_i, row_i, f'{val:.1f}%', ha='center', va='center',
                fontsize=8, color=text_color, fontweight='bold')

plt.colorbar(im, ax=ax, label='Best patch runtime (% of baseline)', shrink=0.8)
fig.savefig(os.path.join(BASE, 'metric1_heatmap.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 7. metric1_per_method.png — Metric B per-method bars ─────────────────────

print('Generating metric1_per_method.png ...')

fig, ax = plt.subplots(figsize=(14, 6), constrained_layout=True)
fig.suptitle('Metric B (Bose): Best Patch Runtime as % of Original — All Experiments\n'
             'Median across repetitions — lower is better',
             fontsize=11, fontweight='bold')

n_exp   = len(all_exp_files)
bar_w   = 0.14
x       = np.arange(len(METHODS_ORDER))
offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_w
exp_colors_list = [COLORS[k] for k in exp_keys]

legend_handles = []
for i, (files, color, lbl) in enumerate(zip(all_exp_files, exp_colors_list,
                                             ['Exp 1: Random sampling',
                                              'Exp 2: UCB + Traditional ops',
                                              'Exp 3: UCB + All ops (incl. LLM)',
                                              'Exp 4: Standard LS + Traditional ops',
                                              'Exp 5: Standard LS + All ops (incl. LLM)'])):
    mb = metric_b_per_method(files)
    vals = [float(np.median(mb.get(m, [100.0]))) for m in METHODS_ORDER]
    bars = ax.bar(x + offsets[i], vals, width=bar_w, color=color, alpha=0.85, label=lbl)
    legend_handles.append(bars)

ax.axhline(100, color='black', linewidth=1.0, linestyle='--', label='Original runtime (100%)', alpha=0.6)
ax.set_xticks(x)
ax.set_xticklabels(METHODS_ORDER, rotation=30, ha='right', fontsize=8)
ax.set_ylabel('Best patch runtime as % of original (↓ better)')
ax.set_ylim(60, 105)
ax.legend(fontsize=8, loc='lower left')
ax.grid(True, axis='y', alpha=0.3)

fig.savefig(os.path.join(BASE, 'metric1_per_method.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── 8. metric1_summary.png — Metric B summary ────────────────────────────────

print('Generating metric1_summary.png ...')

all_rep_means = [metric_b_per_rep(f) for f in all_exp_files]
medians_b     = [float(np.median(r)) if r else 100.0 for r in all_rep_means]
x_labels      = ['Random\n+Trad', 'UCB\n+Trad', 'UCB\n+LLM', 'LS\n+Trad', 'LS\n+LLM']

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
fig.suptitle('Metric B (Bose Metric 1): Runtime Ratio Summary — All Experiments\n'
             'Mean runtime ratio — lower is better',
             fontsize=11, fontweight='bold')

x = np.arange(len(x_labels))
bars = ax1.bar(x, medians_b, color=exp_colors_list, alpha=0.88, width=0.55)
ax1.axhline(100, color='black', linewidth=1.0, linestyle='--', alpha=0.5)
ax1.set_xticks(x)
ax1.set_xticklabels(x_labels, fontsize=9)
ax1.set_ylabel('Mean runtime ratio across 10 methods (%)')
ax1.set_title('Mean runtime ratio — lower is better', fontsize=9)
ax1.set_ylim(min(medians_b) - 3, 102)
ax1.grid(True, axis='y', alpha=0.3)
for bar, val in zip(bars, medians_b):
    ax1.text(bar.get_x() + bar.get_width() / 2, val - 0.6,
             f'{val:.1f}%', ha='center', va='top', fontsize=9, fontweight='bold', color='white')

# Box plot: distribution across methods
mb_all = [metric_b_per_method(f) for f in all_exp_files]
box_data = []
for mb in mb_all:
    vals = [float(np.median(mb.get(m, [100.0]))) for m in METHODS_ORDER]
    box_data.append(vals)

bp = ax2.boxplot(box_data, patch_artist=True, notch=False,
                 medianprops=dict(color='black', linewidth=2))
for patch, color in zip(bp['boxes'], exp_colors_list):
    patch.set_facecolor(color)
    patch.set_alpha(0.75)
ax2.axhline(100, color='black', linewidth=1.0, linestyle='--', alpha=0.5)
ax2.set_xticks(np.arange(1, len(x_labels) + 1))
ax2.set_xticklabels(x_labels, fontsize=9)
ax2.set_ylabel('Per-method median ratio (%)')
ax2.set_title('Distribution across methods', fontsize=9)
ax2.grid(True, axis='y', alpha=0.3)

fig.savefig(os.path.join(BASE, 'metric1_summary.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')

print('\nAll graphs regenerated successfully.')
