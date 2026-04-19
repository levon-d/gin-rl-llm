"""
Generate CSV results + graphs for the 400-step Exp3 run, and compare
against all five 100-step experiments.

Outputs:
  exp3_400steps_results.csv
  400steps_convergence.png         — cumulative best improvement vs step (all 10 methods)
  400steps_summary_totals.png      — Metric A bar chart (styled like jcodec_final_summary_totals.png)
  400steps_metric_b.png            — Metric B comparison (styled like metric1_summary.png)
  400steps_per_method_vs_100.png   — per-method 100-step vs 400-step Exp3 side-by-side

Usage:
    python3 generate_400steps_analysis.py
"""

import csv, os, glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

# ── Paths ─────────────────────────────────────────────────────────────────────

BASE100 = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'runtime_wang_top10')
BASE400 = os.path.dirname(os.path.abspath(__file__))

FILES_400 = {
    # method -> which file holds its authoritative data
    'main':      os.path.join(BASE400, 'exp3_ucb_all_400steps_rep1_20260410_115033.csv'),
    'remaining': os.path.join(BASE400, 'exp3_ucb_all_400steps_remaining_20260412_134757.csv'),
    'filterbs4': os.path.join(BASE400, 'exp3_ucb_all_400steps_filterbs4_20260412_174512.csv'),
}

# Methods that come from specific override files
OVERRIDE = {
    'resample':     'remaining',
    'getPlaneWidth':'remaining',
    'filterBs4':    'filterbs4',
}

EXP1_FILES = sorted(glob.glob(os.path.join(BASE100, 'exp1_random_rep*_20260312_143630.csv')))
EXP2_FILES = sorted(glob.glob(os.path.join(BASE100, 'exp2_ucb_trad_rep*_20260312_143630.csv')))
EXP3_FILES = [
    os.path.join(BASE100, 'exp3_ucb_all_rep1_20260316_230008.csv'),
    os.path.join(BASE100, 'exp3_ucb_all_rep2_20260330_001857.csv'),
    os.path.join(BASE100, 'exp3_ucb_all_rep3_20260330_001857.csv'),
    os.path.join(BASE100, 'exp3_ucb_all_rep4_20260408_201948.csv'),
    os.path.join(BASE100, 'exp3_ucb_all_rep5_20260408_201948.csv'),
]
EXP4_FILES = sorted(glob.glob(os.path.join(BASE100, 'exp4_ls_trad_rep*_20260319_123900.csv'))) + \
             [os.path.join(BASE100, 'exp4_ls_trad_rep6_20260402_015048.csv')]
EXP5_FILES = [
    os.path.join(BASE100, 'exp5_ls_all_rep1_20260323_140041.csv'),
    os.path.join(BASE100, 'exp5_ls_all_rep2_20260331_152947.csv'),
    os.path.join(BASE100, 'exp5_ls_all_rep3_20260401_141651.csv'),
    os.path.join(BASE100, 'exp5_ls_all_rep4_cal_pb08_20260409_212652.csv'),
    os.path.join(BASE100, 'exp5_ls_all_rep5_cal_pb08_20260409_151823.csv'),
]

METHODS_ORDER = [
    'filterBs4', 'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'mergeResidual', 'resample', 'getPlaneWidth',
]

COLORS = {
    'exp1':  'steelblue',
    'exp2':  'darkorange',
    'exp3':  'darkorchid',
    'exp4':  'seagreen',
    'exp5':  'crimson',
    'exp3_400': '#9B2EE0',  # darker purple for 400-step
}

EXP_LABELS = {
    'exp1':     'Exp 1: Random sampling',
    'exp2':     'Exp 2: UCB + Traditional ops',
    'exp3':     'Exp 3: UCB + All ops (incl. LLM)',
    'exp4':     'Exp 4: Standard LS + Traditional ops',
    'exp5':     'Exp 5: Standard LS + All ops (incl. LLM)',
    'exp3_400': 'Exp 3 (400 steps): UCB + All ops',
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def short_name(full_name):
    full_name = (full_name or '').strip('"').strip()
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
                name = short_name(row.get('MethodName', ''))
                try:
                    bl = float((row.get('BaselineRuntime(ms)') or '').strip('"'))
                    pr = float((row.get('PatchRuntime(ms)') or '').strip('"'))
                except ValueError:
                    continue
                compiled = (row.get('Compiled') or '').strip('"').lower() == 'true'
                passed   = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
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
        with open(f, newline='', errors='replace') as fh:
            for row in csv.DictReader(fh):
                try:
                    name   = short_name(row.get('MethodName', ''))
                    it     = int((row.get('Iteration') or '').strip('"'))
                    comp   = (row.get('Compiled') or '').strip('"').lower() == 'true'
                    passed = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
                    rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                    rt     = float(rt_raw.strip('"'))
                except (ValueError, KeyError, TypeError):
                    continue
                if it == -1:
                    if rt < 1e300:
                        m_bl[name] = rt
                elif comp and passed and 0 < rt < 1e300:
                    if name not in m_best or rt < m_best[name]:
                        m_best[name] = rt
        for m in METHODS_ORDER:
            bl   = m_bl.get(m, 0)
            best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
            if bl > 0:
                baselines[m].append(bl)
    return results, baselines


def pct_stats(exp_data, ref_bl):
    meds, maxs = [], []
    for m in METHODS_ORDER:
        bl  = float(np.median(ref_bl.get(m, [1.0]))) or 1.0
        imp = exp_data.get(m, [0.0])
        meds.append(float(np.median(imp)) / bl * 100)
        maxs.append(float(np.max(imp))    / bl * 100)
    return meds, maxs


def metric_b_per_rep(files, is_exp1=False):
    rep_means = []
    if is_exp1:
        for f in files:
            m_bl, m_best = {}, {}
            with open(f, newline='') as fh:
                for row in csv.DictReader(fh):
                    name = short_name(row.get('MethodName', ''))
                    try:
                        bl = float((row.get('BaselineRuntime(ms)') or '').strip('"'))
                        pr = float((row.get('PatchRuntime(ms)') or '').strip('"'))
                    except ValueError:
                        continue
                    compiled = (row.get('Compiled') or '').strip('"').lower() == 'true'
                    passed   = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
                    if bl > 0:
                        m_bl[name] = bl
                    if compiled and passed and pr > 0:
                        if name not in m_best or pr < m_best[name]:
                            m_best[name] = pr
            ratios = [m_best.get(m, m_bl[m]) / m_bl[m] * 100 for m in METHODS_ORDER if m in m_bl]
            if ratios:
                rep_means.append(float(np.mean(ratios)))
        return rep_means
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_best = {}, {}
        with open(f, newline='', errors='replace') as fh:
            for row in csv.DictReader(fh):
                try:
                    name   = short_name(row.get('MethodName', ''))
                    it     = int((row.get('Iteration') or '').strip('"'))
                    comp   = (row.get('Compiled') or '').strip('"').lower() == 'true'
                    passed = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
                    rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                    rt     = float(rt_raw.strip('"'))
                except (ValueError, KeyError, TypeError):
                    continue
                if it == -1 and rt < 1e300:
                    m_bl[name] = rt
                elif it >= 0 and comp and passed and 0 < rt < 1e300:
                    if name not in m_best or rt < m_best[name]:
                        m_best[name] = rt
        ratios = [m_best.get(m, m_bl[m]) / m_bl[m] * 100 for m in METHODS_ORDER if m in m_bl]
        if ratios:
            rep_means.append(float(np.mean(ratios)))
    return rep_means


# ── Load 400-step data ────────────────────────────────────────────────────────

def load_400step_combined():
    """Returns (per-method dict, step-curves dict) from the three source files."""
    all_parsed = {}
    for key, path in FILES_400.items():
        data = {}
        step_data = defaultdict(dict)  # method -> step -> best_rt
        with open(path, newline='', errors='replace') as fh:
            for row in csv.DictReader(fh):
                try:
                    it = int((row.get('Iteration') or '').strip('"'))
                except ValueError:
                    continue
                name   = short_name(row.get('MethodName', ''))
                rt_raw = (row.get('Runtime(ms)') or row.get('Fitness') or '').strip()
                try:
                    rt = float(rt_raw)
                except ValueError:
                    rt = None
                comp   = (row.get('Compiled') or '').strip('"').lower() == 'true'
                passed = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
                if name not in data:
                    data[name] = {'baseline': None, 'best': None, 'steps': 0, 'passing': 0}
                if it == -1:
                    if rt is not None:
                        data[name]['baseline'] = rt
                else:
                    data[name]['steps'] += 1
                    if comp and passed and rt is not None:
                        data[name]['passing'] += 1
                        if data[name]['best'] is None or rt < data[name]['best']:
                            data[name]['best'] = rt
                        step_data[name][it] = min(step_data[name].get(it, rt), rt)
        all_parsed[key] = (data, step_data)

    # Build combined: main is default, override for specific methods
    combined      = {}
    combined_steps = {}
    main_data, main_steps = all_parsed['main']
    for m in METHODS_ORDER:
        src_key = OVERRIDE.get(m, 'main')
        src_data, src_steps = all_parsed[src_key]
        if m in src_data:
            combined[m]       = src_data[m]
            combined_steps[m] = src_steps[m]
        elif m in main_data:
            combined[m]       = main_data[m]
            combined_steps[m] = main_steps[m]

    return combined, combined_steps


print('Loading 400-step data...')
data_400, steps_400 = load_400step_combined()

print('Loading 100-step data...')
exp1             = load_exp1(EXP1_FILES)
exp2, bl2        = load_ls(EXP2_FILES)
exp3, bl3        = load_ls(EXP3_FILES)
exp4, bl4        = load_ls(EXP4_FILES)
exp5, bl5        = load_ls(EXP5_FILES)

# Pooled reference baseline for 100-step Metric A
all_bls = defaultdict(list)
for d in [bl2, bl3, bl4]:
    for m, vals in d.items():
        all_bls[m].extend(vals)
ref_bl = {m: float(np.median(v)) for m, v in all_bls.items() if v}

# Own-baseline Metric A for 400-step
def metric_a_400(data):
    total = 0.0
    for m in METHODS_ORDER:
        d  = data.get(m, {})
        bl = d.get('baseline')
        best = d.get('best')
        if bl and best:
            total += max(bl - best, 0) / bl * 100
    return total

# Metric B for 400-step (single rep)
def metric_b_400(data):
    ratios = []
    for m in METHODS_ORDER:
        d  = data.get(m, {})
        bl = d.get('baseline')
        best = d.get('best')
        if bl:
            ratios.append((best or bl) / bl * 100)
    return float(np.mean(ratios)) if ratios else 100.0


# ── Save CSV ──────────────────────────────────────────────────────────────────

csv_out = os.path.join(BASE400, 'exp3_400steps_results.csv')
print(f'Saving results CSV to {csv_out} ...')
with open(csv_out, 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['Method', 'Baseline(ms)', 'Best(ms)', 'Improvement(%)', 'MetricB(%)', 'Steps', 'Passing', 'PassRate(%)'])
    for m in METHODS_ORDER:
        d    = data_400.get(m, {})
        bl   = d.get('baseline')
        best = d.get('best')
        steps_n  = d.get('steps', 0)
        passing  = d.get('passing', 0)
        imp  = max(bl - best, 0) / bl * 100 if bl and best else 0.0
        mb   = (best or bl) / bl * 100      if bl            else None
        w.writerow([
            m,
            f'{bl:.1f}'  if bl   else '',
            f'{best:.1f}' if best else '',
            f'{imp:.2f}',
            f'{mb:.2f}'  if mb is not None else '',
            steps_n,
            passing,
            f'{passing/steps_n*100:.1f}' if steps_n else '',
        ])
print('  Saved.')


# ── Graph 1: Step convergence ─────────────────────────────────────────────────

print('Generating 400steps_convergence.png ...')

N_STEPS = 400

# Build cumulative best-improvement curve per method
method_curves = {}
for m in METHODS_ORDER:
    d  = data_400.get(m, {})
    bl = d.get('baseline')
    if bl is None:
        continue
    by_step = steps_400.get(m, {})
    curve   = np.zeros(N_STEPS + 1)
    best    = bl
    for step in range(1, N_STEPS + 1):
        if step in by_step:
            best = min(best, by_step[step])
        curve[step] = max(bl - best, 0.0) / bl * 100  # % improvement
    method_curves[m] = curve

# Total across methods
total_curve = np.zeros(N_STEPS + 1)
for c in method_curves.values():
    total_curve += c

# Also build 100-step Exp3 convergence for overlay
def load_100step_curves(files, n_steps=100):
    method_rep_curves = defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_by_step = {}, defaultdict(dict)
        with open(f, newline='', errors='replace') as fh:
            for row in csv.DictReader(fh):
                try:
                    name   = short_name(row.get('MethodName', ''))
                    it     = int((row.get('Iteration') or '').strip('"'))
                    comp   = (row.get('Compiled') or '').strip('"').lower() == 'true'
                    passed = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
                    rt_raw = row.get('Runtime(ms)') or row.get('Fitness') or 'nan'
                    rt     = float(rt_raw.strip('"'))
                except (ValueError, KeyError, TypeError):
                    continue
                if it == -1 and rt < 1e300:
                    m_bl[name] = rt
                elif it >= 0 and comp and passed and 0 < rt < 1e300:
                    m_by_step[name][it] = min(m_by_step[name].get(it, rt), rt)
        for m in METHODS_ORDER:
            if m not in m_bl:
                continue
            bl    = m_bl[m]
            curve = np.zeros(n_steps + 1)
            best  = bl
            for step in range(1, n_steps + 1):
                if step in m_by_step[m]:
                    best = min(best, m_by_step[m][step])
                curve[step] = max(bl - best, 0.0) / bl * 100
            method_rep_curves[m].append(curve)
    avg = {}
    for m in METHODS_ORDER:
        if method_rep_curves[m]:
            avg[m] = np.mean(method_rep_curves[m], axis=0)
    return avg

exp3_100_curves = load_100step_curves(EXP3_FILES, n_steps=100)
total_100 = np.zeros(101)
for m in METHODS_ORDER:
    if m in exp3_100_curves:
        total_100 += exp3_100_curves[m]

steps_x400 = np.arange(N_STEPS + 1)
steps_x100 = np.arange(101)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
fig.suptitle('Exp 3 (UCB + All ops): Convergence of Best Runtime Improvement vs Step',
             fontsize=12, fontweight='bold')

# Left: total aggregated across all methods
ax1.plot(steps_x400, total_curve, color=COLORS['exp3_400'], lw=2.0,
         label='400 steps (single rep)')
ax1.plot(steps_x100, total_100,   color=COLORS['exp3'],     lw=2.0, ls='--',
         label=f'100 steps (avg of {len(EXP3_FILES)} reps)')
ax1.axvline(100, color='grey', lw=1.0, ls=':', alpha=0.7, label='100-step budget')
ax1.set_xlabel('Step')
ax1.set_ylabel('Sum of per-method % improvement (own baseline)')
ax1.set_title('Aggregated across all 10 methods', fontsize=9)
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# Right: per-method curves for the 400-step run
method_colors = plt.cm.tab10(np.linspace(0, 1, len(METHODS_ORDER)))
for i, m in enumerate(METHODS_ORDER):
    if m in method_curves:
        ax2.plot(steps_x400, method_curves[m], color=method_colors[i], lw=1.5,
                 alpha=0.85, label=m)
ax2.axvline(100, color='grey', lw=1.0, ls=':', alpha=0.7, label='100-step budget')
ax2.set_xlabel('Step')
ax2.set_ylabel('Cumulative best improvement (% of own baseline)')
ax2.set_title('Per-method curves — 400-step run', fontsize=9)
ax2.legend(fontsize=7, loc='upper left', ncol=2)
ax2.grid(True, alpha=0.3)

fig.savefig(os.path.join(BASE400, '400steps_convergence.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── Graph 2: Summary totals (Metric A, like jcodec_final_summary_totals.png) ──

print('Generating 400steps_summary_totals.png ...')

# 100-step Metric A values (pooled baseline)
exp1_meds, exp1_maxs = pct_stats(exp1, ref_bl)
exp2_meds, exp2_maxs = pct_stats(exp2, ref_bl)
exp3_meds, exp3_maxs = pct_stats(exp3, ref_bl)
exp4_meds, exp4_maxs = pct_stats(exp4, ref_bl)
exp5_meds, exp5_maxs = pct_stats(exp5, ref_bl)

sum_meds_100 = [sum(exp1_meds), sum(exp2_meds), sum(exp3_meds), sum(exp4_meds), sum(exp5_meds)]
sum_maxs_100 = [sum(exp1_maxs), sum(exp2_maxs), sum(exp3_maxs), sum(exp4_maxs), sum(exp5_maxs)]
per_method_meds_100 = [exp1_meds, exp2_meds, exp3_meds, exp4_meds, exp5_meds]

# 400-step Metric A (own baseline, per-method)
imp_400 = []
for m in METHODS_ORDER:
    d  = data_400.get(m, {})
    bl = d.get('baseline')
    best = d.get('best')
    imp_400.append(max(bl - best, 0) / bl * 100 if bl and best else 0.0)

bar_labels_100 = ['Exp 1\nRandom', 'Exp 2\nUCB+Trad', 'Exp 3\nUCB+LLM\n(100 steps)',
                  'Exp 4\nLS+Trad', 'Exp 5\nLS+LLM']
bar_colors_100 = [COLORS['exp1'], COLORS['exp2'], COLORS['exp3'], COLORS['exp4'], COLORS['exp5']]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), constrained_layout=True)
fig.suptitle('jcodec: Runtime Improvement Summary — All Experiments',
             fontsize=12, fontweight='bold')

# Left: total Metric A bars — 100-step exps + 400-step exp3
x100 = np.arange(5)
bars = ax1.bar(x100, sum_meds_100, color=bar_colors_100, alpha=0.90, width=0.5)
for bar, val in zip(bars, sum_meds_100):
    ax1.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
             f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

# 400-step bar separately, offset to the right
x400 = 5
ax1.bar(x400, sum(imp_400), color=COLORS['exp3_400'], alpha=0.90, width=0.5,
        label='_nolegend_')
ax1.text(x400, sum(imp_400) + 1.5, f'{sum(imp_400):.1f}%',
         ha='center', va='bottom', fontsize=9, fontweight='bold', color=COLORS['exp3_400'])

ax1.set_xticks(list(x100) + [x400])
ax1.set_xticklabels(bar_labels_100 + ['Exp 3\nUCB+LLM\n(400 steps)'], fontsize=8)
ax1.set_ylabel('Sum of % improvements across all 10 methods')
ax1.set_title('Total improvement (Metric A)', fontsize=9)
ax1.grid(True, axis='y', alpha=0.3)

# Add divider between 100-step and 400-step
ax1.axvline(4.5, color='grey', lw=1.0, ls='--', alpha=0.5)
ax1.text(4.55, ax1.get_ylim()[1] * 0.97, '400 steps →', fontsize=7,
         color='grey', va='top')

# Right: per-method improvement — 100-step exps + 400-step
n_exp = 6
bar_h = 0.12
offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_h
ym = np.arange(len(METHODS_ORDER))

right_labels = ['Exp 1: Random', 'Exp 2: UCB+Trad', 'Exp 3: UCB+LLM (100 steps)',
                'Exp 4: LS+Trad', 'Exp 5: LS+LLM', 'Exp 3: UCB+LLM (400 steps)']
all_meds = per_method_meds_100 + [imp_400]
all_colors = bar_colors_100 + [COLORS['exp3_400']]

for meds, offset, color, lbl in zip(all_meds, offsets, all_colors, right_labels):
    ls = '--' if '400' in lbl else '-'
    ax2.barh(ym + offset, meds, height=bar_h, color=color, alpha=0.88, label=lbl,
             linestyle=ls, edgecolor='white' if '400' not in lbl else color)

ax2.set_yticks(ym)
ax2.set_yticklabels(METHODS_ORDER, fontsize=8)
ax2.set_xlabel('Improvement (%)')
ax2.set_title('Per-method improvement — median across repetitions\n(100-step exps) / single rep (400-step)', fontsize=9)
ax2.legend(fontsize=8, loc='lower right')
ax2.grid(True, axis='x', alpha=0.3)
ax2.axvline(0, color='grey', linewidth=0.7)

fig.savefig(os.path.join(BASE400, '400steps_summary_totals.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── Graph 3: Metric B comparison (like metric1_summary.png) ──────────────────

print('Generating 400steps_metric_b.png ...')

mb1 = metric_b_per_rep(EXP1_FILES, is_exp1=True)
mb2 = metric_b_per_rep(EXP2_FILES)
mb3 = metric_b_per_rep(EXP3_FILES)
mb4 = metric_b_per_rep(EXP4_FILES)
mb5 = metric_b_per_rep(EXP5_FILES)
mb3_400 = metric_b_400(data_400)  # single value

rep_data = [mb1, mb2, mb3, mb4, mb5]
exp_keys = ['exp1', 'exp2', 'exp3', 'exp4', 'exp5']
x_labels = ['Exp 1\nRandom', 'Exp 2\nUCB+Trad', 'Exp 3\nUCB+LLM\n(100 steps)',
            'Exp 4\nLS+Trad', 'Exp 5\nLS+LLM']

fig, ax = plt.subplots(figsize=(11, 5), constrained_layout=True)
fig.suptitle('jcodec: Metric B — Best Runtime as % of Baseline (lower is better)',
             fontsize=12, fontweight='bold')

positions = list(range(5))
for pos, (vals, key) in enumerate(zip(rep_data, exp_keys)):
    med = np.median(vals)
    color = COLORS[key]
    # box-style: scatter jitter + median line
    jitter = np.random.RandomState(42).uniform(-0.15, 0.15, len(vals))
    ax.scatter([pos + j for j in jitter], vals, color=color, alpha=0.6, s=60, zorder=3)
    ax.hlines(med, pos - 0.25, pos + 0.25, colors=color, lw=2.5, zorder=4)
    ax.text(pos, med - 1.2, f'{med:.1f}%', ha='center', va='top', fontsize=9,
            fontweight='bold', color=color)

# 400-step as a diamond marker
ax.scatter([5], [mb3_400], color=COLORS['exp3_400'], marker='D', s=120, zorder=5,
           label='Exp 3: UCB+LLM (400 steps, single rep)')
ax.text(5, mb3_400 - 1.2, f'{mb3_400:.1f}%', ha='center', va='top', fontsize=9,
        fontweight='bold', color=COLORS['exp3_400'])

ax.axvline(4.5, color='grey', lw=1.0, ls='--', alpha=0.5)
ax.text(4.55, ax.get_ylim()[1] if ax.get_ylim()[1] < 120 else 105,
        '400 steps →', fontsize=7, color='grey', va='top')

ax.set_xticks(list(range(5)) + [5])
ax.set_xticklabels(x_labels + ['Exp 3\nUCB+LLM\n(400 steps)'], fontsize=8)
ax.set_ylabel('Mean(best_rt / baseline_rt) × 100   [%]')
ax.set_ylim(top=min(ax.get_ylim()[1] + 5, 115))
ax.axhline(100, color='black', lw=0.8, ls=':', alpha=0.5, label='Baseline (100%)')
ax.grid(True, axis='y', alpha=0.3)
ax.legend(fontsize=9)

# Annotate per-rep count
for pos, vals in enumerate(rep_data):
    ax.text(pos, ax.get_ylim()[0] + 0.5, f'n={len(vals)}', ha='center',
            fontsize=7, color='grey')

fig.savefig(os.path.join(BASE400, '400steps_metric_b.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


# ── Graph 4: Per-method 100-step vs 400-step Exp3 ────────────────────────────

print('Generating 400steps_per_method_vs_100.png ...')

# 100-step Exp3: median per method improvement (own baseline)
exp3_own_bl = defaultdict(list)
exp3_own_imp = defaultdict(list)
for f in [f for f in EXP3_FILES if os.path.exists(f)]:
    m_bl, m_best = {}, {}
    with open(f, newline='', errors='replace') as fh:
        for row in csv.DictReader(fh):
            try:
                name   = short_name(row.get('MethodName', ''))
                it     = int((row.get('Iteration') or '').strip('"'))
                comp   = (row.get('Compiled') or '').strip('"').lower() == 'true'
                passed = (row.get('AllTestsPassed') or '').strip('"').lower() == 'true'
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
        bl   = m_bl.get(m)
        best = m_best.get(m, bl)
        if bl:
            exp3_own_imp[m].append(max(bl - best, 0) / bl * 100)

exp3_100_med = [float(np.median(exp3_own_imp.get(m, [0.0]))) for m in METHODS_ORDER]
exp3_400_imp = [
    max(data_400.get(m, {}).get('baseline', 0) - (data_400.get(m, {}).get('best') or data_400.get(m, {}).get('baseline', 0)), 0)
    / data_400.get(m, {}).get('baseline', 1) * 100
    if data_400.get(m, {}).get('baseline') else 0.0
    for m in METHODS_ORDER
]

y = np.arange(len(METHODS_ORDER))
bar_h = 0.35

fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
fig.suptitle('Exp 3 (UCB + All ops): Per-method Improvement — 100 vs 400 Steps',
             fontsize=12, fontweight='bold')

bars100 = ax.barh(y + bar_h / 2, exp3_100_med, height=bar_h,
                  color=COLORS['exp3'], alpha=0.85,
                  label=f'100 steps (median of {len(EXP3_FILES)} reps)')
bars400 = ax.barh(y - bar_h / 2, exp3_400_imp, height=bar_h,
                  color='#E65100', alpha=0.85,
                  label='400 steps (single rep)')

for i, (v100, v400) in enumerate(zip(exp3_100_med, exp3_400_imp)):
    if v100 > 0.5:
        ax.text(v100 + 0.3, i + bar_h / 2, f'{v100:.1f}%', va='center', fontsize=7)
    if v400 > 0.5:
        ax.text(v400 + 0.3, i - bar_h / 2, f'{v400:.1f}%', va='center', fontsize=7,
                color='#E65100')

ax.set_yticks(y)
ax.set_yticklabels(METHODS_ORDER, fontsize=9)
ax.set_xlabel('Runtime improvement (% of own baseline)')
ax.axvline(0, color='grey', lw=0.7)
ax.grid(True, axis='x', alpha=0.3)
ax.legend(fontsize=9)

fig.savefig(os.path.join(BASE400, '400steps_per_method_vs_100.png'), dpi=150, bbox_inches='tight')
plt.close(fig)
print('  Saved.')


print('\nDone. Files written to:', BASE400)
print('  exp3_400steps_results.csv')
print('  400steps_convergence.png')
print('  400steps_summary_totals.png')
print('  400steps_metric_b.png')
print('  400steps_per_method_vs_100.png')
