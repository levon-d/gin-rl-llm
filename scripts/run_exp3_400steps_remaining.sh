#!/bin/bash

# Rerun just resample + getPlaneWidth for the 400-step Exp3 run.
# These two methods failed with an exception in the original run.
#
# Usage:
#   nohup ./run_exp3_400steps_remaining.sh > /dev/null 2>&1 &
#
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(400steps_remaining|done|WARNING)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_resample_getplanewidth.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10_400steps"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=400
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60
REP_TIMEOUT=86400  # 24 hours

seed=1123
output_file="$RESULTS_DIR/exp3_ucb_all_400steps_remaining_${TIMESTAMP}.csv"
rl_log_file="$RESULTS_DIR/exp3_rl_log_400steps_remaining_${TIMESTAMP}.csv"

mkdir -p "$RESULTS_DIR"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "Exp3 400steps — resample + getPlaneWidth (remaining)" | tee -a "$LOG"
echo "$(date) | seed=$seed | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

echo "--- Exp3 400steps_remaining started (seed=$seed) at $(date) ---" | tee -a "$LOG"

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
    echo "WARNING: Exp3 400steps_remaining timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
else
    echo "Exp3 400steps_remaining done: $output_file" | tee -a "$LOG"
fi

echo "========================================" | tee -a "$LOG"
echo "Done at $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
