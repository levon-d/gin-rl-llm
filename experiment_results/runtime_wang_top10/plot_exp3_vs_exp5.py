"""
Plot Exp 3 vs Exp 5 comparison from summary CSVs.

Exp 3: UCB Local Search + Traditional + LLM operators  (rep 2)
Exp 5: Standard Local Search + Traditional + LLM operators (rep 1)

Produces two figures:
  1. Grouped bar chart: improvement % per method
  2. Horizontal bar chart: TOTAL improvement per experiment

Usage:
    python3 plot_exp3_vs_exp5.py
    python3 plot_exp3_vs_exp5.py --show
"""

import csv, os, argparse
import matplotlib.pyplot as plt
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))

EXP3_SUMMARY = BASE + '/exp3_results_summary_final.csv'
EXP5_SUMMARY = BASE + '/exp5_results_summary_final.csv'

METHODS_ORDER = [
    'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'filterBs4',
    'mergeResidual', 'resample', 'getPlaneWidth',
]


def load_summary(path):
    """Load summary CSV. Returns dict: method_short -> improvement%."""
    results = {}
    total_impr = None
    with open(path, newline='') as fh:
        reader = csv.reader(fh)
        # Skip header line(s) — first non-empty line starting with 'Method' is the header
        for row in reader:
            if not row or row[0].strip() in ('', ) or row[0].startswith('EXPERIMENT'):
                continue
            if row[0].strip() == 'Method':
                break
        for row in reader:
            if not row or len(row) < 4:
                continue
            name = row[0].strip()
            if name == 'TOTAL':
                try:
                    total_impr = float(row[-1])
                except ValueError:
                    pass
                continue
            try:
                impr = float(row[-1])
            except ValueError:
                continue
            results[name] = impr
    return results, total_impr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--show', action='store_true')
    args = parser.parse_args()

    exp3, exp3_total = load_summary(EXP3_SUMMARY)
    exp5, exp5_total = load_summary(EXP5_SUMMARY)

    print('Exp 3 (UCB+LLM, rep 2):')
    for m in METHODS_ORDER:
        print(f'  {m}: {exp3.get(m, 0):.2f}%')
    print(f'  TOTAL: {exp3_total:.2f}%')

    print('Exp 5 (Standard LS+LLM, rep 1):')
    for m in METHODS_ORDER:
        print(f'  {m}: {exp5.get(m, 0):.2f}%')
    print(f'  TOTAL: {exp5_total:.2f}%')

    e3_vals = [exp3.get(m, 0.0) for m in METHODS_ORDER]
    e5_vals = [exp5.get(m, 0.0) for m in METHODS_ORDER]

    # ---- Figure 1: Grouped bar chart per method ----
    fig1, ax1 = plt.subplots(figsize=(14, 5))

    x = np.arange(len(METHODS_ORDER))
    width = 0.35

    ax1.bar(x - width/2, e3_vals, width,
            label='Exp 3: UCB + LLM (rep 2)',
            color='darkorchid', alpha=0.85)
    ax1.bar(x + width/2, e5_vals, width,
            label='Exp 5: Standard LS + LLM (rep 1)',
            color='teal', alpha=0.85)

    ax1.set_xlabel('Method')
    ax1.set_ylabel('Improvement over baseline (%)')
    ax1.set_title(
        'Best Improvement Found per Method: UCB+LLM (Exp 3) vs Standard Local Search+LLM (Exp 5)'
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
        out1 = BASE + '/exp3_vs_exp5_comparison.png'
        fig1.savefig(out1, dpi=150, bbox_inches='tight')
        print(f'Saved: {out1}')
    plt.close(fig1)

    # ---- Figure 2: Horizontal bar — TOTAL improvement per experiment ----
    fig2, ax2 = plt.subplots(figsize=(7, 3.5))

    labels = ['Exp 3: UCB\nLocal Search + LLM\n(rep 2)',
              'Exp 5: Standard\nLocal Search + LLM\n(rep 1)']
    totals = [exp3_total or 0.0, exp5_total or 0.0]
    colors = ['darkorchid', 'teal']

    y = np.arange(len(labels))
    bars = ax2.barh(y, totals, color=colors, alpha=0.85, height=0.4)

    ax2.set_yticks(y)
    ax2.set_yticklabels(labels, fontsize=10)
    ax2.set_xlabel('Total improvement over baseline (%)')
    ax2.set_title('Total Runtime Improvement: UCB+LLM (Exp 3) vs Standard LS+LLM (Exp 5)\n'
                  '(summed across all 10 methods)')
    ax2.axvline(0, color='grey', linewidth=0.8)
    ax2.grid(True, axis='x', alpha=0.3)

    for bar, val in zip(bars, totals):
        ax2.text(max(val + 0.3, 0.3), bar.get_y() + bar.get_height() / 2,
                 f'{val:.1f}%', va='center', fontsize=11, fontweight='bold')

    plt.tight_layout()

    if args.show:
        plt.show()
    else:
        out2 = BASE + '/exp3_vs_exp5_total_summary.png'
        fig2.savefig(out2, dpi=150, bbox_inches='tight')
        print(f'Saved: {out2}')
    plt.close(fig2)


if __name__ == '__main__':
    main()
