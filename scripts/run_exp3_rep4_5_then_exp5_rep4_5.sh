#!/bin/bash

# Run Exp3 (UCB+All) reps 4 & 5, then Exp5 (LS+All) reps 4 & 5, sequentially.
# All four use LLM operators — sequential to avoid concurrent Ollama calls.
#
# Usage:
#   nohup ./run_exp3_rep4_5_then_exp5_rep4_5.sh > /dev/null 2>&1 &
#
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp [35] Rep|done|WARNING|complete)"

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
REP_TIMEOUT=57600  # 16 hours per rep

mkdir -p "$RESULTS_DIR"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "Starting Exp3 reps 4+5, Exp5 reps 4+5" | tee -a "$LOG"
echo "$(date) | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

# --- Experiment 3: UCB + All operators (reps 4 and 5) ---

for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    rl_log_file="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 3 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

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

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: Exp 3 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp 3 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done

echo "Exp 3 reps 4+5 complete at $(date)" | tee -a "$LOG"

# --- Experiment 5: LocalSearch + All operators (reps 4 and 5) ---

for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 5 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JCODEC_DIR" \
        -p jcodec \
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

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: Exp 5 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp 5 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done

echo "Exp 5 reps 4+5 complete at $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "All done at $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
