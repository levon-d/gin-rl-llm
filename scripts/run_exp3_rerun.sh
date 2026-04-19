#!/bin/bash

# Experiment 3 rerun — reps 1, 3, 4, 5 only (rep 2 already complete)
# Runs in parallel: batch 1 = reps 1, 3 | batch 2 = reps 4, 5
# Includes subprocess-kill fix for hanging test evaluations.
#
# Usage:  nohup ./run_exp3_rerun.sh > /dev/null 2>&1 &
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp 3|done|WARNING|Batch|complete)"
# Quick step count:
#   for rep in 1 3 4 5; do f=~/repos/gin-rl/experiment_results/runtime_wang_top10/exp3_rl_log_rep${rep}_TIMESTAMP.csv; echo "Rep $rep: $(( $(wc -l < $f) - 1 )) steps"; done

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60    # seconds per LLM call
REP_TIMEOUT=28800  # max seconds per rep before killing (8 hours)

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "Starting Experiment 3 RERUN (reps 1,3,4,5) at $(date)" | tee -a "$LOG"
echo "LLM Model: $LLM_MODEL | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "Fix applied: subprocess-kill on step timeout" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "=== EXPERIMENT 3 RERUN: UCB Local Search (Traditional + LLM: $LLM_MODEL) ===" | tee -a "$LOG"

# Run a single rep — called as a background job
run_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    local rl_log_file="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 3, Rep $rep started ($(date)) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
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
        -rl ucb \
        -ops all \
        -rllog "$rl_log_file" \
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: Exp 3 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp 3 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# --- Batch 1: reps 1, 3 in parallel ---
echo "--- Batch 1: Reps 1, 3 running in parallel ---" | tee -a "$LOG"
run_rep 1 &
run_rep 3 &
wait
echo "--- Batch 1 complete ($(date)) ---" | tee -a "$LOG"

# --- Batch 2: reps 4, 5 in parallel ---
echo "--- Batch 2: Reps 4, 5 running in parallel ---" | tee -a "$LOG"
run_rep 4 &
run_rep 5 &
wait
echo "--- Batch 2 complete ($(date)) ---" | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "Experiment 3 rerun complete at $(date)" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
echo "NOTE: Combine with existing rep 2 data (timestamp 20260316_174940) for full 5-rep analysis" | tee -a "$LOG"
