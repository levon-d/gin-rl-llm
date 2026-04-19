#!/bin/bash

# Experiment 4: Local Search, Traditional Operators Only (no RL)
# Runs reps 1-3 in parallel (Batch 1), then reps 4-5 in parallel (Batch 2).
# Baseline comparison for Exp 3 (UCB RL) — isolates benefit of RL operator selection.
#
# Usage:  nohup ./run_exp4_localsearch_trad.sh > /dev/null 2>&1 &
# Monitor: tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp 4|done|WARNING|Batch|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
REP_TIMEOUT=28800  # 8 hours per rep

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "Starting Experiment 4 (LocalSearch Traditional) at $(date) | Timestamp: $TIMESTAMP" | tee -a "$LOG"

run_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp4_ls_trad_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 4 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JCODEC_DIR" \
        -p jcodec \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -ms $seed \
        -is $((seed + 100)) \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: Exp 4 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp 4 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

echo "--- Exp 4 Batch 1: Reps 1, 2, 3 ---" | tee -a "$LOG"
run_rep 1 &
run_rep 2 &
run_rep 3 &
wait
echo "--- Exp 4 Batch 1 complete ($(date)) ---" | tee -a "$LOG"

echo "--- Exp 4 Batch 2: Reps 4, 5 ---" | tee -a "$LOG"
run_rep 4 &
run_rep 5 &
wait
echo "--- Exp 4 Batch 2 complete ($(date)) ---" | tee -a "$LOG"

echo "Experiment 4 complete at $(date)" | tee -a "$LOG"
