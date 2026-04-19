#!/bin/bash

# JUnit4: Experiments 3 + 5 (LLM, sequential)
# Exp 3: UCB + Traditional + LLM operators
# Exp 5: Standard LS + Traditional + LLM operators
# Sequential to avoid concurrent Ollama calls.
#
# Usage:  nohup ./run_junit4_exp3_exp5.sh > /dev/null 2>&1 &
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(junit4|Exp [35]|done|WARNING|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JUNIT4_DIR="/Users/""/repos/junit4"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/junit4_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_junit4_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
NUM_REPS=3
LLM_MODEL="qwen2.5-coder:1.5b"
LLM_TIMEOUT=30
REP_TIMEOUT=57600  # 16 hours per rep

mkdir -p "$RESULTS_DIR"

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "=== Starting JUnit4 Exp3+Exp5 (LLM, sequential) at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"
echo "LLM: $LLM_MODEL | Timeout: ${LLM_TIMEOUT}s | Reps: $NUM_REPS" | tee -a "$LOG"

# --- Experiment 3: UCB + All (Traditional + LLM) ---
run_exp3_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    local rl_log_file="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp3 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
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
        echo "WARNING: JUnit4 Exp3 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp3 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# --- Experiment 5: Standard LS + All (Traditional + LLM) ---
run_exp5_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp5 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: JUnit4 Exp5 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp5 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# Run all sequentially: Exp3 reps then Exp5 reps
for rep in $(seq 1 $NUM_REPS); do
    run_exp3_rep $rep
done

for rep in $(seq 1 $NUM_REPS); do
    run_exp5_rep $rep
done

echo "=== JUnit4 Exp3+Exp5 complete at $(date) ===" | tee -a "$LOG"
