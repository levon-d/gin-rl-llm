"""
Generate comparison graphs for gson experiments.

Figures:
  1. gson_summary_totals.png  — left: total Metric A bar chart; right: per-method grouped barh
  2. gson_metric_b.png        — Bose Metric 1 bar chart (mean ratio, lower = better)

Canonical files (runtime_gson_top2/):
  Exp1: exp1_random_rep*.csv          (3 reps, RandomSampler)
  Exp2: exp2_ucb_trad_rep*.csv        (3 reps, RLLocalSearchRuntime)
  Exp3: exp3_ucb_all_rep*.csv         (3 reps, RLLocalSearchRuntime)
  Exp4: exp4_ls_trad_rep*.csv         (3 reps, LocalSearchRuntime)
  Exp5: exp5_ls_all_rep*.csv          (3 reps, LocalSearchRuntime)

Usage:
    python3 gen_gson_graphs.py
"""

import csv, glob, os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict

BASE    = os.path.dirname(os.path.abspath(__file__))
METHODS = ['deserializeToDate', 'parse']

COLORS = {
    'exp1': 'steelblue',
    'exp2': 'darkorange',
    'exp3': 'darkorchid',
    'exp4': 'seagreen',
    'exp5': 'crimson',
}
LABELS = {
    'exp1': 'Exp 1\nRandom',
    'exp2': 'Exp 2\nUCB+Trad',
    'exp3': 'Exp 3\nUCB+LLM',
    'exp4': 'Exp 4\nLS+Trad',
    'exp5': 'Exp 5\nLS+LLM',
}
LEGEND_LABELS = {k: v.replace('\n', ' ') for k, v in LABELS.items()}


def short(full):
    full = full.strip('"').strip()
    for k in METHODS:
        if k in full: return k
    return full.split('(')[0].split('.')[-1]


def load_random(files):
    results, baselines = defaultdict(list), defaultdict(list)
    for f in files:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            for row in csv.DictReader(fh):
                name = short(row.get('MethodName', ''))
                try:
                    bl = float((row.get('BaselineRuntime(ms)') or '').strip('"'))
                    pr = float((row.get('PatchRuntime(ms)') or '').strip('"'))
                    ok = (((row.get('Compiled') or '').strip('"').lower() == 'true') and
                          ((row.get('AllTestsPassed') or '').strip('"').lower() == 'true'))
                except ValueError:
                    continue
                if bl > 0: m_bl[name] = bl
                if ok and pr > 0 and (name not in m_best or pr < m_best[name]):
                    m_best[name] = pr
        for m in METHODS:
            bl = m_bl.get(m, 0); best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
            if bl > 0: baselines[m].append(bl)
    return results, baselines


def load_ls(files):
    results, baselines = defaultdict(list), defaultdict(list)
    for f in [f for f in files if os.path.exists(f)]:
        m_bl, m_best = {}, {}
        with open(f, newline='') as fh:
            rows = list(csv.DictReader(fh))
        for row in rows:
            try:
                name = short(row.get('MethodName', ''))
                it   = int((row.get('Iteration') or '').strip('"'))
                rt   = float((row.get('Runtime(ms)') or row.get('Fitness') or 'nan').strip('"'))
                ok   = (((row.get('Compiled') or '').strip('"').lower() == 'true') and
                        ((row.get('AllTestsPassed') or '').strip('"').lower() == 'true'))
            except (ValueError, TypeError):
                continue
            if it == -1:
                if rt < 1e300: m_bl[name] = rt
                continue
            if name not in m_bl: continue
            if ok and 0 < rt < 1e300 and (name not in m_best or rt < m_best[name]):
                m_best[name] = rt
        for m in METHODS:
            bl = m_bl.get(m, 0); best = m_best.get(m, bl)
            results[m].append(max(bl - best, 0.0) if bl > 0 else 0.0)
            if bl > 0: baselines[m].append(bl)
    return results, baselines


def find(pattern):
    return sorted(f for f in glob.glob(os.path.join(BASE, pattern))
                  if '_summary' not in f)


def pct_med(data, m, ref_bl):
    bl = ref_bl.get(m, 1.0)
    return float(np.median(data.get(m, [0.0]))) / bl * 100

def pct_max(data, m, ref_bl):
    bl = ref_bl.get(m, 1.0)
    return float(np.max(data.get(m, [0.0]))) / bl * 100

def bose_ratio(data, bls, m, ref_bl=None):
    """Compute median(best_patch / baseline * 100) across reps.
    If ref_bl is given, use it as the denominator (consistent with Metric A pooled baseline)
    to avoid per-rep baseline noise inflating or deflating results."""
    imp = data.get(m, [])
    bl  = bls.get(m, [])
    if not imp or not bl: return 100.0
    n = min(len(imp), len(bl))
    if ref_bl is not None:
        denom = ref_bl.get(m, None)
        if denom and denom > 0:
            best_patches = [bl[i] - imp[i] for i in range(n)]
            return float(np.median([bp / denom * 100 for bp in best_patches]))
    return float(np.median([(bl[i] - imp[i]) / bl[i] * 100 for i in range(n)]))


BASE_500 = os.path.join(os.path.dirname(BASE), 'runtime_gson_top2_500steps')


def find500(pattern):
    return sorted(f for f in glob.glob(os.path.join(BASE_500, pattern))
                  if '_summary' not in f)


def main():
    # ── load 100-step ────────────────────────────────────────────────────────
    exp1, bl1 = load_random(find('exp1_random_rep*.csv'))
    exp2, bl2 = load_ls(find('exp2_ucb_trad_rep*.csv'))
    exp3, bl3 = load_ls(find('exp3_ucb_all_rep*.csv'))
    exp4, bl4 = load_ls(find('exp4_ls_trad_rep*.csv'))
    exp5, bl5 = load_ls(find('exp5_ls_all_rep*.csv'))

    # ── load 500-step ────────────────────────────────────────────────────────
    exp2_500, bl2_500 = load_ls(find500('exp2_ucb_trad_rep*.csv'))
    exp3_500, bl3_500 = load_ls(find500('exp3_ucb_all_rep*.csv'))
    exp4_500, bl4_500 = load_ls(find500('exp4_ls_trad_rep*.csv'))

    all_data = {
        'exp1': (exp1, bl1), 'exp2': (exp2, bl2), 'exp3': (exp3, bl3),
        'exp4': (exp4, bl4), 'exp5': (exp5, bl5),
    }
    EXPS = ['exp1', 'exp2', 'exp3', 'exp4', 'exp5']

    # Reference baseline: pool Exp2+Exp3+Exp4 (100-step)
    all_bls = defaultdict(list)
    for k in ['exp2', 'exp3', 'exp4']:
        for m, v in all_data[k][1].items(): all_bls[m].extend(v)
    ref_bl = {m: float(np.median(v)) for m, v in all_bls.items() if v}

    # 500-step reference baseline: pool Exp2+Exp3+Exp4 @500
    all_data_500 = {
        'exp2': (exp2_500, bl2_500),
        'exp3': (exp3_500, bl3_500),
        'exp4': (exp4_500, bl4_500),
    }
    EXPS_500 = ['exp2', 'exp3', 'exp4']
    all_bls_500 = defaultdict(list)
    for k in EXPS_500:
        for m, v in all_data_500[k][1].items(): all_bls_500[m].extend(v)
    ref_bl_500 = {m: float(np.median(v)) for m, v in all_bls_500.items() if v}

    # ── print tables ─────────────────────────────────────────────────────────
    print("=== 100-step results ===")
    print("Metric A — Sum of median % improvements")
    for k in EXPS:
        data, bls = all_data[k]
        meds = [pct_med(data, m, ref_bl) for m in METHODS]
        print(f"  {LEGEND_LABELS[k]:<18}  " +
              "  ".join(f"{m}: {v:+.1f}%" for m, v in zip(METHODS, meds)) +
              f"  TOTAL: {sum(meds):+.1f}%")

    print("\nMetric B — Mean Bose ratio (lower = better)")
    for k in EXPS:
        data, bls = all_data[k]
        ratios = [bose_ratio(data, bls, m, ref_bl) for m in METHODS]
        print(f"  {LEGEND_LABELS[k]:<18}  " +
              "  ".join(f"{m}: {v:.1f}%" for m, v in zip(METHODS, ratios)) +
              f"  MEAN: {np.mean(ratios):.1f}%")

    print("\n=== 500-step results (Exp2, Exp3, Exp4 only) ===")
    print("Metric A — Sum of median % improvements")
    LABELS_500 = {'exp2': 'Exp 2 UCB+Trad', 'exp3': 'Exp 3 UCB+LLM', 'exp4': 'Exp 4 LS+Trad'}
    for k in EXPS_500:
        data, bls = all_data_500[k]
        meds = [pct_med(data, m, ref_bl_500) for m in METHODS]
        print(f"  {LABELS_500[k]:<18}  " +
              "  ".join(f"{m}: {v:+.1f}%" for m, v in zip(METHODS, meds)) +
              f"  TOTAL: {sum(meds):+.1f}%")

    print("\nMetric B — Mean Bose ratio (lower = better)")
    for k in EXPS_500:
        data, bls = all_data_500[k]
        ratios = [bose_ratio(data, bls, m, ref_bl_500) for m in METHODS]
        print(f"  {LABELS_500[k]:<18}  " +
              "  ".join(f"{m}: {v:.1f}%" for m, v in zip(METHODS, ratios)) +
              f"  MEAN: {np.mean(ratios):.1f}%")

    # ── Figure 1: Summary totals + per-method ───────────────────────────────
    colors = [COLORS[k] for k in EXPS]
    x = np.arange(len(EXPS))

    sum_meds = [sum(pct_med(all_data[k][0], m, ref_bl) for m in METHODS) for k in EXPS]
    sum_maxs = [sum(pct_max(all_data[k][0], m, ref_bl) for m in METHODS) for k in EXPS]
    per_method_meds = [[pct_med(all_data[k][0], m, ref_bl) for m in METHODS] for k in EXPS]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    fig.suptitle('gson: Runtime Improvement Summary — All Experiments (100 steps)',
                 fontsize=12, fontweight='bold')

    # Left: totals
    ax1.bar(x, sum_maxs, color=colors, alpha=0.25, width=0.55, label='Best single-rep (upper bound)')
    bars = ax1.bar(x, sum_meds, color=colors, alpha=0.90, width=0.55, label='Median across reps')
    ax1.set_xticks(x)
    ax1.set_xticklabels([LABELS[k] for k in EXPS], fontsize=9)
    ax1.set_ylabel('Sum of % improvements across all methods')
    ax1.set_title('Total improvement (Metric A)', fontsize=9)
    ax1.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars, sum_meds):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 0.5,
                 f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')
    ax1.legend(fontsize=8, loc='upper left')

    # Right: per-method
    n_exp = len(EXPS)
    bar_h = 0.14
    offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_h
    ym = np.arange(len(METHODS))
    for meds, offset, color, k in zip(per_method_meds, offsets, colors, EXPS):
        ax2.barh(ym + offset, meds, height=bar_h, color=color, alpha=0.88,
                 label=LEGEND_LABELS[k])
    ax2.set_yticks(ym)
    ax2.set_yticklabels(METHODS, fontsize=9)
    ax2.set_xlabel('Median improvement (% of reference baseline runtime)')
    ax2.set_title('Per-method improvement — median across repetitions', fontsize=9)
    ax2.legend(fontsize=8, loc='lower right')
    ax2.grid(True, axis='x', alpha=0.3)
    ax2.axvline(0, color='grey', linewidth=0.7)

    out1 = os.path.join(BASE, 'gson_summary_totals.png')
    fig.savefig(out1, dpi=150, bbox_inches='tight')
    print(f'\nSaved: {out1}')
    plt.close(fig)

    # ── Figure 2: Metric B bar chart ────────────────────────────────────────
    b_means = []
    b_per   = []
    for k in EXPS:
        data, bls = all_data[k]
        ratios = [bose_ratio(data, bls, m, ref_bl) for m in METHODS]
        b_per.append(ratios)
        b_means.append(float(np.mean(ratios)))

    fig2, (ax3, ax4) = plt.subplots(1, 2, figsize=(13, 5), constrained_layout=True)
    fig2.suptitle('gson: Bose Metric 1 — best_runtime / baseline (lower = better)',
                  fontsize=12, fontweight='bold')

    # Left: mean ratio
    bars2 = ax3.bar(x, b_means, color=colors, alpha=0.88, width=0.55)
    ax3.axhline(100, color='grey', lw=0.8, linestyle='--', label='No improvement (100%)')
    ax3.set_xticks(x)
    ax3.set_xticklabels([LABELS[k] for k in EXPS], fontsize=9)
    ax3.set_ylabel('Mean Bose ratio (%) across methods')
    ax3.set_title('Metric B — mean ratio (lower = better)', fontsize=9)
    ax3.set_ylim(80, 102)
    ax3.grid(True, axis='y', alpha=0.3)
    ax3.legend(fontsize=8)
    for bar, val in zip(bars2, b_means):
        ax3.text(bar.get_x() + bar.get_width() / 2, val - 0.5,
                 f'{val:.1f}%', ha='center', va='top', fontsize=9, fontweight='bold',
                 color='white')

    # Right: per-method grouped barh
    n_exp = len(EXPS)
    bar_h = 0.14
    offsets = np.linspace(-(n_exp - 1) / 2, (n_exp - 1) / 2, n_exp) * bar_h
    ym = np.arange(len(METHODS))
    for ratios, offset, color, k in zip(b_per, offsets, colors, EXPS):
        ax4.barh(ym + offset, ratios, height=bar_h, color=color, alpha=0.88,
                 label=LEGEND_LABELS[k])
    ax4.axvline(100, color='grey', lw=0.8, linestyle='--')
    ax4.set_yticks(ym)
    ax4.set_yticklabels(METHODS, fontsize=9)
    ax4.set_xlabel('Bose ratio (%) — lower = better')
    ax4.set_title('Per-method Bose ratio', fontsize=9)
    ax4.legend(fontsize=8, loc='lower right')
    ax4.grid(True, axis='x', alpha=0.3)

    out2 = os.path.join(BASE, 'gson_metric_b.png')
    fig2.savefig(out2, dpi=150, bbox_inches='tight')
    print(f'Saved: {out2}')
    plt.close(fig2)

    # ── Figure 3: 500-step comparison (Exp2, Exp3, Exp4) ────────────────────
    COLORS_500 = {k: COLORS[k] for k in EXPS_500}
    LABELS_500_short = {
        'exp2': 'Exp 2\nUCB+Trad',
        'exp3': 'Exp 3\nUCB+LLM',
        'exp4': 'Exp 4\nLS+Trad',
    }
    LEGEND_500 = {k: v.replace('\n', ' ') for k, v in LABELS_500_short.items()}

    x3 = np.arange(len(EXPS_500))
    colors3 = [COLORS_500[k] for k in EXPS_500]
    sum_meds_500 = [sum(pct_med(all_data_500[k][0], m, ref_bl_500) for m in METHODS) for k in EXPS_500]
    sum_maxs_500 = [sum(pct_max(all_data_500[k][0], m, ref_bl_500) for m in METHODS) for k in EXPS_500]
    per_method_meds_500 = [[pct_med(all_data_500[k][0], m, ref_bl_500) for m in METHODS] for k in EXPS_500]

    b_means_500, b_per_500 = [], []
    for k in EXPS_500:
        data, bls = all_data_500[k]
        ratios = [bose_ratio(data, bls, m, ref_bl_500) for m in METHODS]
        b_per_500.append(ratios)
        b_means_500.append(float(np.mean(ratios)))

    fig3, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    fig3.suptitle('gson: 500-step Comparison — Exp2 (UCB+Trad) vs Exp3 (UCB+LLM) vs Exp4 (LS+Trad)',
                  fontsize=12, fontweight='bold')
    ax5, ax6, ax7, ax8 = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]

    # Top-left: Metric A totals
    bars5 = ax5.bar(x3, sum_maxs_500, color=colors3, alpha=0.25, width=0.55)
    bars5m = ax5.bar(x3, sum_meds_500, color=colors3, alpha=0.90, width=0.55)
    ax5.set_xticks(x3)
    ax5.set_xticklabels([LABELS_500_short[k] for k in EXPS_500], fontsize=9)
    ax5.set_ylabel('Sum of % improvements across methods')
    ax5.set_title('Metric A — Total improvement (500 steps)', fontsize=9)
    ax5.grid(True, axis='y', alpha=0.3)
    for bar, val in zip(bars5m, sum_meds_500):
        ax5.text(bar.get_x() + bar.get_width() / 2, val + 0.3,
                 f'{val:.1f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Top-right: Metric A per-method barh
    n3 = len(EXPS_500)
    bar_h3 = 0.20
    offsets3 = np.linspace(-(n3 - 1) / 2, (n3 - 1) / 2, n3) * bar_h3
    ym3 = np.arange(len(METHODS))
    for meds, offset, color, k in zip(per_method_meds_500, offsets3, colors3, EXPS_500):
        ax6.barh(ym3 + offset, meds, height=bar_h3, color=color, alpha=0.88,
                 label=LEGEND_500[k])
    ax6.set_yticks(ym3)
    ax6.set_yticklabels(METHODS, fontsize=9)
    ax6.set_xlabel('Median improvement (% of ref baseline runtime)')
    ax6.set_title('Per-method improvement — median across reps', fontsize=9)
    ax6.legend(fontsize=8, loc='lower right')
    ax6.grid(True, axis='x', alpha=0.3)
    ax6.axvline(0, color='grey', linewidth=0.7)

    # Bottom-left: Metric B means
    bars7 = ax7.bar(x3, b_means_500, color=colors3, alpha=0.88, width=0.55)
    ax7.axhline(100, color='grey', lw=0.8, linestyle='--', label='No improvement')
    ax7.set_xticks(x3)
    ax7.set_xticklabels([LABELS_500_short[k] for k in EXPS_500], fontsize=9)
    ax7.set_ylabel('Mean Bose ratio (%) across methods')
    ax7.set_title('Metric B — mean Bose ratio (lower = better, 500 steps)', fontsize=9)
    ylim_lo = max(75, min(b_means_500) - 5)
    ax7.set_ylim(ylim_lo, 102)
    ax7.grid(True, axis='y', alpha=0.3)
    ax7.legend(fontsize=8)
    for bar, val in zip(bars7, b_means_500):
        ax7.text(bar.get_x() + bar.get_width() / 2, val - 0.3,
                 f'{val:.1f}%', ha='center', va='top', fontsize=9, fontweight='bold',
                 color='white')

    # Bottom-right: Metric B per-method barh
    for ratios, offset, color, k in zip(b_per_500, offsets3, colors3, EXPS_500):
        ax8.barh(ym3 + offset, ratios, height=bar_h3, color=color, alpha=0.88,
                 label=LEGEND_500[k])
    ax8.axvline(100, color='grey', lw=0.8, linestyle='--')
    ax8.set_yticks(ym3)
    ax8.set_yticklabels(METHODS, fontsize=9)
    ax8.set_xlabel('Bose ratio (%) — lower = better')
    ax8.set_title('Per-method Bose ratio (500 steps)', fontsize=9)
    ax8.legend(fontsize=8, loc='lower right')
    ax8.grid(True, axis='x', alpha=0.3)

    out3 = os.path.join(BASE, 'gson_500step_comparison.png')
    fig3.savefig(out3, dpi=150, bbox_inches='tight')
    print(f'Saved: {out3}')
    plt.close(fig3)


if __name__ == '__main__':
    main()
