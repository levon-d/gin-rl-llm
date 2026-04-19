"""
Generate exp4_results_summary.csv from Exp 4 (Standard Local Search) output files.

CSV columns: MethodName, Iteration, EvaluationNumber, Patch, Compiled, AllTestsPassed,
             TotalExecutionTime(ms), Fitness, FitnessImprovement
Fitness == runtime in ms; baseline row has Iteration == "-1".

Run from this directory:
    python3 generate_exp4_summary.py
"""

import csv, os, glob, statistics

BASE = os.path.dirname(os.path.abspath(__file__))

# Auto-detect latest Exp4 timestamp
_ts_files = sorted(
    f for f in glob.glob(BASE + '/exp4_ls_trad_rep1_*.csv')
    if 'summary' not in f
)
if not _ts_files:
    raise FileNotFoundError('No exp4_ls_trad_rep1_*.csv found in ' + BASE)
TIMESTAMP = '_'.join(os.path.basename(_ts_files[-1]).replace('.csv', '').split('_')[-2:])
print('Using timestamp:', TIMESTAMP)

# Auto-detect reps
REPS = sorted(
    int(os.path.basename(f).split('_rep')[1].split('_')[0])
    for f in glob.glob(BASE + f'/exp4_ls_trad_rep*_{TIMESTAMP}.csv')
)
print(f'Found {len(REPS)} reps: {REPS}')

METHODS_ORDER = [
    'filterBs', 'estimateQPix', 'takeSafe', 'getLumaPred4x4',
    'filterBlockEdgeHoris', 'filterBlockEdgeVert', 'filterBs4',
    'mergeResidual', 'resample', 'getPlaneWidth',
]

# filterBs( matches filterBs (not filterBs4), all others by substring
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


def parse_exp4_rep(rep):
    """
    Parse one Exp4 rep CSV file using csv.reader (required: method names contain commas).
    Returns dict: short_name -> (baseline_rt, best_rt)
    """
    filepath = BASE + f'/exp4_ls_trad_rep{rep}_{TIMESTAMP}.csv'
    baselines = {}  # short -> float
    bests = {}      # short -> float (minimum passing runtime)

    with open(filepath, newline='') as fh:
        reader = csv.reader(fh)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 8:
                continue
            method_full = row[0].strip()
            iteration = row[1].strip()
            compiled = row[4].strip().lower()
            passed = row[5].strip().lower() == 'true'
            try:
                fitness = float(row[7])
            except ValueError:
                continue

            short = short_name(method_full)

            if iteration == '-1':
                # Baseline row
                baselines[short] = fitness
            else:
                # Regular step: record best passing runtime
                if passed and fitness < 1e300:
                    if short not in bests or fitness < bests[short]:
                        bests[short] = fitness

    return baselines, bests


# Collect per-rep data
# exp4_data[short] = list of (baseline, best, reduction, pct) per rep
exp4_data = {short: [] for _, short in METHODS_KEYS}

for rep in REPS:
    baselines, bests = parse_exp4_rep(rep)
    for _, short in METHODS_KEYS:
        baseline = baselines.get(short, 0.0)
        best = bests.get(short, baseline)  # if nothing improved, best == baseline
        reduction = baseline - best
        pct = 100.0 * reduction / baseline if baseline > 0 else 0.0
        exp4_data[short].append((baseline, best, reduction, pct))

# TOTAL per rep
exp4_total = []
for i in range(len(REPS)):
    total_baseline = sum(exp4_data[s][i][0] for _, s in METHODS_KEYS)
    total_best = sum(exp4_data[s][i][1] for _, s in METHODS_KEYS)
    total_red = total_baseline - total_best
    total_pct = 100.0 * total_red / total_baseline if total_baseline > 0 else 0.0
    exp4_total.append((total_baseline, total_best, total_red, total_pct))

# Build column header matching existing summary format
per_method_header = ['Method']
for r in REPS:
    per_method_header += [
        f'Baseline_R{r}(ms)', f'Best_R{r}(ms)',
        f'Reduction_R{r}(ms)', f'Impr_R{r}(%)'
    ]
per_method_header += ['MeanReduction(ms)', 'MeanImprovement(%)']

# Write output CSV
out = BASE + '/exp4_results_summary.csv'
with open(out, 'w', newline='') as fh:
    w = csv.writer(fh)
    w.writerow(['EXPERIMENT 4: Standard Local Search (Traditional Operators)'])
    w.writerow(per_method_header)

    for _, short in METHODS_KEYS:
        vals = exp4_data[short]
        reds = [v[2] for v in vals]
        pcts = [v[3] for v in vals]
        row = [short]
        for v in vals:
            row += [round(v[0], 2), round(v[1], 2), round(v[2], 2), round(v[3], 2)]
        row += [round(sum(reds) / len(REPS), 2), round(sum(pcts) / len(REPS), 2)]
        w.writerow(row)

    # TOTAL row
    reds = [v[2] for v in exp4_total]
    pcts = [v[3] for v in exp4_total]
    row = ['TOTAL']
    for v in exp4_total:
        row += [round(v[0], 2), round(v[1], 2), round(v[2], 2), round(v[3], 2)]
    row += [round(sum(reds) / len(REPS), 2), round(sum(pcts) / len(REPS), 2)]
    w.writerow(row)

print('Written to:', out)

# ---- Print summary table to stdout ----
col_w = 24
print()
print('=' * 90)
print('EXPERIMENT 4: Standard Local Search (Traditional Operators)')
print(f'Timestamp: {TIMESTAMP}  |  Reps: {len(REPS)}')
print('=' * 90)
header = f"{'Method':<{col_w}}"
for r in REPS:
    header += f"{'Baseline':>10}{'Best':>10}{'Reduc(ms)':>10}{'Impr(%)':>9}"
header += f"{'MeanReduc':>10}{'MeanImpr':>9}"
print(header)
print('-' * 90)

for _, short in METHODS_KEYS:
    vals = exp4_data[short]
    reds = [v[2] for v in vals]
    pcts = [v[3] for v in vals]
    line = f"{short:<{col_w}}"
    for v in vals:
        line += f"{v[0]:>10.1f}{v[1]:>10.1f}{v[2]:>10.2f}{v[3]:>9.2f}"
    line += f"{sum(reds)/len(REPS):>10.2f}{sum(pcts)/len(REPS):>9.2f}"
    print(line)

print('-' * 90)
reds = [v[2] for v in exp4_total]
pcts = [v[3] for v in exp4_total]
line = f"{'TOTAL':<{col_w}}"
for v in exp4_total:
    line += f"{v[0]:>10.1f}{v[1]:>10.1f}{v[2]:>10.2f}{v[3]:>9.2f}"
line += f"{sum(reds)/len(REPS):>10.2f}{sum(pcts)/len(REPS):>9.2f}"
print(line)
print('=' * 90)

# Per-rep improvement% summary
print()
print('Per-rep mean improvement across all methods:')
for i, rep in enumerate(REPS):
    rep_pcts = [exp4_data[s][i][3] for _, s in METHODS_KEYS]
    print(f'  Rep {rep}: mean={statistics.mean(rep_pcts):.2f}%  total_impr={exp4_total[i][3]:.2f}%')
