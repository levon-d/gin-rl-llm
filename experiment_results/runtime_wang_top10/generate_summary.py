"""
Generate results_summary.csv from Exp 1 and Exp 2 output files.
Run from this directory: python3 generate_summary.py
"""

import csv, os, glob, statistics

base = os.path.dirname(os.path.abspath(__file__))

# Auto-detect latest timestamp
_ts_files = sorted(f for f in glob.glob(base + '/exp1_random_rep1_*.csv') if 'summary' not in f)
if not _ts_files:
    raise FileNotFoundError('No exp1_random_rep1_*.csv found in ' + base)
TIMESTAMP = '_'.join(os.path.basename(_ts_files[-1]).replace('.csv','').split('_')[-2:])
print('Using timestamp:', TIMESTAMP)

# Auto-detect number of reps
REPS = sorted(int(os.path.basename(f).split('_rep')[1].split('_')[0])
              for f in glob.glob(base + f'/exp1_random_rep*_{TIMESTAMP}.csv')
              if 'summary' not in f)

methods_short = [
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
    for key, short in methods_short:
        if key in method:
            return short
    return method

# ---- Exp 1: patch statistics ----
exp1_compiling = []
exp1_passing = []
exp1_improving = []

for rep in REPS:
    f = base + '/exp1_random_rep' + str(rep) + '_' + TIMESTAMP + '_summary.csv'
    with open(f) as fh:
        for line in fh:
            parts = line.strip().split(',')
            if parts[0] == 'CompilingPatches': exp1_compiling.append(float(parts[2]))
            if parts[0] == 'PassingPatches':   exp1_passing.append(float(parts[2]))
            if parts[0] == 'ImprovingPatches': exp1_improving.append(float(parts[2]))

# ---- Exp 1: best patch found per method ----
exp1_best = {}  # short -> list of (baseline, bestRuntime, reduction, pct) per rep

for rep in REPS:
    f = base + '/exp1_random_rep' + str(rep) + '_' + TIMESTAMP + '.csv'
    method_best = {}
    method_baseline = {}

    with open(f) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            passed = row['AllTestsPassed'].strip().lower() == 'true'
            method = row['MethodName'].strip()
            short = short_name(method)
            baseline = float(row['BaselineRuntime(ms)'])
            patch_rt = float(row['PatchRuntime(ms)'])

            method_baseline[short] = baseline

            if passed and patch_rt > 0 and patch_rt < baseline:
                if short not in method_best or patch_rt < method_best[short]:
                    method_best[short] = patch_rt

    for _, short in methods_short:
        baseline = method_baseline.get(short, 0)
        best = method_best.get(short, baseline)
        reduction = baseline - best
        pct = 100.0 * reduction / baseline if baseline > 0 else 0.0
        if short not in exp1_best:
            exp1_best[short] = []
        exp1_best[short].append((baseline, best, reduction, pct))

# Exp 1 TOTAL per rep
exp1_total = []
for i in range(len(REPS)):
    total_baseline = sum(exp1_best[s][i][0] for _, s in methods_short)
    total_best = sum(exp1_best[s][i][1] for _, s in methods_short)
    total_red = total_baseline - total_best
    total_pct = 100.0 * total_red / total_baseline if total_baseline > 0 else 0
    exp1_total.append((total_baseline, total_best, total_red, total_pct))

# ---- Exp 2: per-method runtime summary ----
exp2_data = {}

for rep in REPS:
    f = base + '/exp2_rl_log_rep' + str(rep) + '_' + TIMESTAMP + '_runtime_summary.csv'
    with open(f) as fh:
        reader = csv.reader(fh)
        next(reader)
        for row in reader:
            name = row[0].strip('"')
            short = 'TOTAL' if name == 'TOTAL' else short_name(name)
            if short not in exp2_data:
                exp2_data[short] = []
            exp2_data[short].append((float(row[1]), float(row[2]), float(row[3]), float(row[4])))

# ---- Write summary CSV ----
out = base + '/results_summary.csv'
with open(out, 'w', newline='') as fh:
    w = csv.writer(fh)

    # Section 1: Exp 1 patch stats
    w.writerow(['EXPERIMENT 1: Random Sampling (Baseline) — Patch Statistics'])
    rep_labels = [f'Rep{r}' for r in REPS]
    w.writerow(['Metric'] + rep_labels + ['Mean', 'StdDev'])
    for label, vals in [('CompilingPatches(%)', exp1_compiling),
                        ('PassingPatches(%)', exp1_passing),
                        ('ImprovingPatches(%)', exp1_improving)]:
        w.writerow([label] + vals +
                   [round(sum(vals)/len(REPS), 2), round(statistics.stdev(vals), 2)])
    w.writerow([])

    # Section 2: Exp 1 best-per-method
    per_method_header = ['Method']
    for r in REPS:
        per_method_header += [f'Baseline_R{r}(ms)', f'Best_R{r}(ms)',
                               f'Reduction_R{r}(ms)', f'Impr_R{r}(%)']
    per_method_header += ['MeanReduction(ms)', 'MeanImprovement(%)']

    w.writerow(['EXPERIMENT 1: Random Sampling — Best Patch Found Per Method'])
    w.writerow(per_method_header)
    for _, short in methods_short:
        vals = exp1_best[short]
        reds = [v[2] for v in vals]
        pcts = [v[3] for v in vals]
        row = [short]
        for v in vals:
            row += [v[0], v[1], round(v[2], 2), round(v[3], 2)]
        row += [round(sum(reds)/len(REPS), 2), round(sum(pcts)/len(REPS), 2)]
        w.writerow(row)
    reds = [v[2] for v in exp1_total]
    pcts = [v[3] for v in exp1_total]
    row = ['TOTAL']
    for v in exp1_total:
        row += [round(v[0], 2), round(v[1], 2), round(v[2], 2), round(v[3], 2)]
    row += [round(sum(reds)/len(REPS), 2), round(sum(pcts)/len(REPS), 2)]
    w.writerow(row)
    w.writerow([])

    # Section 3: Exp 2
    w.writerow(['EXPERIMENT 2: UCB Local Search (Traditional Operators)'])
    w.writerow(per_method_header)
    for short in [s for _, s in methods_short] + ['TOTAL']:
        vals = exp2_data.get(short, [])
        if not vals:
            continue
        reds = [v[2] for v in vals]
        pcts = [v[3] for v in vals]
        row = [short]
        for v in vals:
            row += [v[0], v[1], round(v[2], 2), round(v[3], 2)]
        row += [round(sum(reds)/len(REPS), 2), round(sum(pcts)/len(REPS), 2)]
        w.writerow(row)
    w.writerow([])

    # Section 4: Head-to-head
    w.writerow([f'HEAD-TO-HEAD: Best Found Per Method (averaged over {len(REPS)} reps)'])
    w.writerow(['Method', 'Exp1_MeanReduction(ms)', 'Exp1_MeanImprovement(%)',
                          'Exp2_MeanReduction(ms)', 'Exp2_MeanImprovement(%)'])
    for _, short in methods_short:
        e1 = exp1_best[short]
        e2 = exp2_data.get(short, [])
        e1_red = round(sum(v[2] for v in e1)/len(REPS), 2)
        e1_pct = round(sum(v[3] for v in e1)/len(REPS), 2)
        e2_red = round(sum(v[2] for v in e2)/len(REPS), 2) if e2 else 'N/A'
        e2_pct = round(sum(v[3] for v in e2)/len(REPS), 2) if e2 else 'N/A'
        w.writerow([short, e1_red, e1_pct, e2_red, e2_pct])
    e1t_red = round(sum(v[2] for v in exp1_total)/len(REPS), 2)
    e1t_pct = round(sum(v[3] for v in exp1_total)/len(REPS), 2)
    e2t = exp2_data.get('TOTAL', [])
    e2t_red = round(sum(v[2] for v in e2t)/len(REPS), 2)
    e2t_pct = round(sum(v[3] for v in e2t)/len(REPS), 2)
    w.writerow(['TOTAL', e1t_red, e1t_pct, e2t_red, e2t_pct])

print('Written to:', out)
