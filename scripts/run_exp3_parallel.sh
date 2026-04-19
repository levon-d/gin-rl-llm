#!/bin/bash

# Experiment 3 — parallel version (runs reps concurrently)
# Runs 3 reps in parallel, then 2 reps in parallel.
# Each rep has its own output files and an 8-hour gtimeout safety net.
#
# Usage:  ./run_exp3_parallel.sh
# Monitor milestone completions:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp 3|done|WARNING|complete)"
# Monitor step progress per rep:
#   awk -F',' 'NR>1 {print $1}' ~/repos/gin-rl/experiment_results/runtime_wang_top10/exp3_rl_log_rep1_TIMESTAMP.csv | sort -n | uniq -c

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_REPETITIONS=5
NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60    # seconds per LLM call
REP_TIMEOUT=28800  # max seconds per rep before killing (8 hours)

mkdir -p "$RESULTS_DIR"

echo "Starting Experiment 3 (PARALLEL) at $(date)" | tee -a "$LOG"
echo "LLM Model: $LLM_MODEL | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "=== EXPERIMENT 3: UCB Local Search (Traditional + LLM: $LLM_MODEL) ===" | tee -a "$LOG"

# Run a single rep — called as a background job
run_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    local rl_log_file="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 3, Rep $rep/$NUM_REPETITIONS started ($(date)) ---" | tee -a "$LOG"

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

# --- Batch 1: reps 1, 2, 3 in parallel ---
echo "--- Batch 1: Reps 1, 2, 3 running in parallel ---" | tee -a "$LOG"
run_rep 1 &
run_rep 2 &
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
echo "Experiment 3 (parallel) complete at $(date)" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
