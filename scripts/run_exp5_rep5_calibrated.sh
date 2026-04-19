#!/bin/bash

# Run Exp5 (LS+All) rep 5 with calibrated LLM probability (-pb 0.8 = ~20% LLM rate).
#
# Rationale: the default combinedProbablity=0.5 gives 50% LLM calls regardless of
# operator performance. UCB (Exp3) naturally converges to ~20% LLM selection across
# all reps (range 17-22%). Setting -pb 0.8 (P(LLM) = 1 - 0.8 = 20%) makes this rep
# use a rate comparable to UCB's organic selection rate, enabling a fairer comparison.
#
# Usage:
#   nohup ./run_exp5_rep5_calibrated.sh > /dev/null 2>&1 &
#
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp 5 Rep 5|done|WARNING)"

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
LLM_TIMEOUT=60
REP_TIMEOUT=57600  # 16 hours
LLM_PROB=0.8       # P(LLM) = 1 - 0.8 = 20%, matching UCB's natural selection rate

rep=5
seed=$((123 + rep * 1000))
output_file="$RESULTS_DIR/exp5_ls_all_rep${rep}_cal_pb08_${TIMESTAMP}.csv"

mkdir -p "$RESULTS_DIR"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
echo "Exp5 Rep 5 (calibrated -pb 0.8, ~20% LLM)" | tee -a "$LOG"
echo "$(date) | seed=$seed | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"

echo "--- Exp 5 Rep $rep started (seed=$seed, pb=0.8) at $(date) ---" | tee -a "$LOG"

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
    -pb $LLM_PROB \
    >> "$LOG" 2>&1

exit_code=$?
if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
    echo "WARNING: Exp 5 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
else
    echo "Exp 5 Rep $rep (calibrated) done: $output_file" | tee -a "$LOG"
fi

echo "========================================" | tee -a "$LOG"
echo "All done at $(date)" | tee -a "$LOG"
echo "========================================" | tee -a "$LOG"
