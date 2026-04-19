#!/bin/bash

# JUnit4: Experiments 1, 2, 4 (non-LLM, all parallel)
# Exp 1: Random Sampling (baseline)
# Exp 2: UCB + Traditional operators
# Exp 4: Standard Local Search + Traditional operators
#
# Usage:  nohup ./run_junit4_exp1_exp2_exp4.sh > /dev/null 2>&1 &
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(junit4|done|WARNING|Batch|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JUNIT4_DIR="/Users/""/repos/junit4"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/junit4_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_junit4_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
REP_TIMEOUT=28800  # 8 hours per rep

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "=== Starting JUnit4 Exp1+Exp2+Exp4 at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"

# --- Experiment 1: Random Sampling ---
run_exp1_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp1 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RandomSampler \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -pn $NUM_STEPS \
        -ps 1 \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -rp $seed \
        -rm $((seed + 100)) \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: JUnit4 Exp1 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp1 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# --- Experiment 2: UCB + Traditional ---
run_exp2_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
    local rl_log_file="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp2 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

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
        echo "WARNING: JUnit4 Exp2 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp2 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# --- Experiment 4: Standard LS + Traditional ---
run_exp4_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp4_ls_trad_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp4 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

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
        echo "WARNING: JUnit4 Exp4 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp4 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

echo "--- Batch 1: Reps 1,2,3 for Exp1+Exp2+Exp4 ---" | tee -a "$LOG"
run_exp1_rep 1 &
run_exp1_rep 2 &
run_exp1_rep 3 &
run_exp2_rep 1 &
run_exp2_rep 2 &
run_exp2_rep 3 &
run_exp4_rep 1 &
run_exp4_rep 2 &
run_exp4_rep 3 &
wait
echo "--- Batch 1 complete ($(date)) ---" | tee -a "$LOG"

echo "--- Batch 2: Reps 4,5 for Exp1+Exp2+Exp4 ---" | tee -a "$LOG"
run_exp1_rep 4 &
run_exp1_rep 5 &
run_exp2_rep 4 &
run_exp2_rep 5 &
run_exp4_rep 4 &
run_exp4_rep 5 &
wait
echo "--- Batch 2 complete ($(date)) ---" | tee -a "$LOG"

echo "=== JUnit4 Exp1+Exp2+Exp4 complete at $(date) ===" | tee -a "$LOG"
