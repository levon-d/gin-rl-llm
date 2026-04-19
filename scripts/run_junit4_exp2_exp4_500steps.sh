#!/bin/bash

# JUnit4: Experiments 2 & 4 with 500 steps (cold-start test)
# Exp 2: UCB + Traditional operators (500 steps per method)
# Exp 4: Standard Local Search + Traditional operators (500 steps per method)
#
# Usage:  nohup ./run_junit4_exp2_exp4_500steps.sh > /dev/null 2>&1 &
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(junit4|done|WARNING|Batch|complete|500)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JUNIT4_DIR="/Users/""/repos/junit4"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/junit4_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_junit4_top10_500steps"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=500
REP_TIMEOUT=57600  # 16 hours per rep

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "=== Starting JUnit4 Exp2+Exp4 500steps at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"

# --- Experiment 2: UCB + Traditional (500 steps) ---
run_exp2_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
    local rl_log_file="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp2-500 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -ms $seed \
        -is $((seed + 100)) \
        -rl ucb \
        -ops traditional \
        -rllog "$rl_log_file" \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: JUnit4 Exp2-500 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp2-500 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# --- Experiment 4: Standard LS + Traditional (500 steps) ---
run_exp4_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp4_ls_trad_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp4-500 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
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
        echo "WARNING: JUnit4 Exp4-500 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp4-500 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

echo "--- Batch 1: Reps 1,2,3 for Exp2+Exp4 (500 steps) ---" | tee -a "$LOG"
run_exp2_rep 1 &
run_exp2_rep 2 &
run_exp2_rep 3 &
run_exp4_rep 1 &
run_exp4_rep 2 &
run_exp4_rep 3 &
wait
echo "--- Batch 1 complete ($(date)) ---" | tee -a "$LOG"

echo "--- Batch 2: Reps 4,5 for Exp2+Exp4 (500 steps) ---" | tee -a "$LOG"
run_exp2_rep 4 &
run_exp2_rep 5 &
run_exp4_rep 4 &
run_exp4_rep 5 &
wait
echo "--- Batch 2 complete ($(date)) ---" | tee -a "$LOG"

echo "=== JUnit4 Exp2+Exp4 500steps complete at $(date) ===" | tee -a "$LOG"
