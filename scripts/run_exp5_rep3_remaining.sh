#!/bin/bash
# Rerun Exp5 Rep3 for the 6 methods that crashed (exit code 255 from sleep interrupt bug).
# Appends to the SAME output CSV as the original Rep3 run so results can be merged.

PROJECT_DIR="/Users/""/repos/gin-rl"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_exp5_rep3_remaining.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
LOG="$PROJECT_DIR/experiment_run_bg.log"

# Same timestamp and seed as the original Rep3 run so results merge correctly
OUTPUT_FILE="$RESULTS_DIR/exp5_ls_all_rep3_20260331_152947.csv"
SEED=3123   # 123 + 3*1000

NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60
STEP_TIMEOUT=180

JCODEC_DIR="/Users/""/repos/jcodec_exp5_rep3"

echo "" | tee -a "$LOG"
echo "=== Exp5 Rep3 REMAINING 6 methods at $(date) ===" | tee -a "$LOG"
echo "Output: $OUTPUT_FILE (appending)" | tee -a "$LOG"

cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
    -d "$JCODEC_DIR" \
    -p jcodec \
    -m "$METHOD_FILE" \
    -o "$OUTPUT_FILE" \
    -h "$MAVEN_HOME" \
    -j \
    -in $NUM_STEPS \
    -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
    -ms $SEED \
    -is $((SEED + 100)) \
    -st $STEP_TIMEOUT \
    -mt "$LLM_MODEL" \
    -mo $LLM_TIMEOUT \
    >> "$LOG" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Exp5 Rep3 remaining done" | tee -a "$LOG"
else
    echo "WARNING: Exp5 Rep3 remaining exited with code $exit_code" | tee -a "$LOG"
fi
echo "Finished at $(date)" | tee -a "$LOG"
