"""
Regenerate jcodec_final_summary_totals.png with all 5 experiments.

Left panel : Total improvement (sum of per-method median % over reference baseline)
             Solid bar = median across reps; shaded bar = best single-rep improvement
             Arrow annotation marks the shaded (upper bound) bar instead of legend.
Right panel: Per-method grouped horizontal bar chart (median improvement %).

Canonical file sets:
  Exp1: exp1_random_rep*_20260312_143630.csv         (5 reps)
  Exp2: exp2_ucb_trad_rep*_20260312_143630.csv        (5 reps)
  Exp3: exp3_ucb_all_rep1_20260316_230008.csv +
        exp3_ucb_all_rep{2,3}_20260330_001857.csv     (3 reps)
  Exp4: exp4_ls_trad_rep*_20260319_123900.csv +
        exp4_ls_trad_rep6_20260402_015048.csv         (6 reps)
  Exp5: exp5_ls_all_rep{1,2}_20260331_152947.csv +
        exp5_ls_all_rep3_20260401_141651.csv          (3 reps)

Usage:
    python3 gen_summary_totals.py
"""

import csv, glob, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

METHODS = [
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


def short_name(full):
    full = full.strip('"').strip()
    for key in sorted(METHODS, key=len, reverse=True):
        if key in full:
            return key
    return full.split('(')[0].split('.')[-1]


def load_random(files):
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
        for m in METHODS:
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
            reader = csv.DictReader(fh)
            rows = list(reader)
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
        for m in METHODS:
            bl   = m_bl.get(m, 0)
            best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
            if bl > 0:
                baselines[m].append(bl)
    return results, baselines


def pct_stats(exp_data, ref_bl):
    meds, maxs = [], []
    for m in METHODS:
        bl  = float(np.median(ref_bl.get(m, [1.0]))) or 1.0
        imp = exp_data.get(m, [0.0])
        meds.append(float(np.median(imp)) / bl * 100)
        maxs.append(float(np.max(imp)) / bl * 100)
    return meds, maxs


def main():
    exp1             = load_random(EXP1_FILES)
    exp2, bl2        = load_ls(EXP2_FILES)
    exp3, bl3        = load_ls(EXP3_FILES)
    exp4, bl4        = load_ls(EXP4_FILES)
    exp5, bl5        = load_ls(EXP5_FILES)

    # Reference baseline: pool Exp2+Exp3+Exp4, median per method
    all_bls = defaultdict(list)
    for d in [bl2, bl3, bl4]:
        for m, vals in d.items():
            all_bls[m].extend(vals)
    ref_bl = {m: np.median(v) for m, v in all_bls.items() if v}

    labels = ['Exp 1\nRandom', 'Exp 2\nUCB+Trad', 'Exp 3\nUCB+LLM', 'Exp 4\nLS+Trad', 'Exp 5\nLS+LLM']
    colors = [COLORS[k] for k in ('exp1', 'exp2', 'exp3', 'exp4', 'exp5')]
    exps   = [exp1, exp2, exp3, exp4, exp5]

    sum_meds, sum_maxs, per_method_meds = [], [], []
    for e in exps:
        meds, maxs = pct_stats(e, ref_bl)
        sum_meds.append(sum(meds))
        sum_maxs.append(sum(maxs))
        per_method_meds.append(meds)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5), constrained_layout=True)
    fig.suptitle('jcodec: Runtime Improvement Summary — All Experiments (100 steps)',
                 fontsize=12, fontweight='bold')

    # ── Left: total bar chart ──────────────────────────────────────────────────
    x = np.arange(len(labels))
    # shaded bar (max/upper bound) drawn first so solid bar overlaps it
    ax1.bar(x, sum_maxs, color=colors, alpha=0.25, width=0.55)
    bars = ax1.bar(x, sum_meds, color=colors, alpha=0.90, width=0.55)
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylabel('Sum of % improvements across all 10 methods')
    ax1.set_title('Total improvement (sum of per-method % over baseline)', fontsize=9)
    ax1.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, sum_meds):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 1.5,
                 f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Arrow annotation instead of legend: point at shaded extension of Exp3 bar
    exp3_idx   = 2  # Exp3 is the third bar
    exp3_max   = sum_maxs[exp3_idx]
    exp3_med   = sum_meds[exp3_idx]
    mid_shade  = (exp3_med + exp3_max) / 2   # mid-point of the shaded extension
    arrow_x    = exp3_idx + 0.55             # text anchor to the right
    arrow_y    = mid_shade * 0.88

    ax1.annotate(
        'Best single-rep\nimprovement\n(upper bound)',
        xy=(exp3_idx, mid_shade),
        xytext=(arrow_x + 0.25, arrow_y),
        fontsize=8,
        ha='left', va='center',
        arrowprops=dict(arrowstyle='->', color='#555555', lw=1.2,
                        connectionstyle='arc3,rad=-0.15'),
        color='#444444',
    )

    # ── Right: per-method grouped horizontal bars ──────────────────────────────
    n_exp   = len(exps)
    bar_h   = 0.14
    offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_h
    ym      = np.arange(len(METHODS))
    right_labels = ['Exp 1: Random', 'Exp 2: UCB+Trad', 'Exp 3: UCB+LLM',
                    'Exp 4: LS+Trad', 'Exp 5: LS+LLM']
    for meds, offset, color, lbl in zip(per_method_meds, offsets, colors, right_labels):
        ax2.barh(ym + offset, meds, height=bar_h, color=color, alpha=0.88, label=lbl)
    ax2.set_yticks(ym)
    ax2.set_yticklabels(METHODS, fontsize=8)
    ax2.set_xlabel('Median improvement (% of reference baseline runtime)')
    ax2.set_title('Per-method improvement — median across repetitions', fontsize=9)
    ax2.legend(fontsize=8, loc='lower right')
    ax2.grid(True, axis='x', alpha=0.3)
    ax2.axvline(0, color='grey', linewidth=0.7)

    out = os.path.join(BASE, 'jcodec_final_summary_totals.png')
    fig.savefig(out, dpi=150, bbox_inches='tight')
    print(f'Saved: {out}')
    plt.close(fig)

    print('\nSum of median % improvements:')
    for lbl, val in zip(labels, sum_meds):
        print(f'  {lbl.replace(chr(10), " "):<18} {val:.1f}%')


if __name__ == '__main__':
    main()
