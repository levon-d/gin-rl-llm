#!/bin/bash
PROJECT_DIR="/Users/""/repos/gin-rl"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
LOG="$PROJECT_DIR/experiment_run_bg.log"
JCODEC_DIR="/Users/""/repos/jcodec_exp5_rep3"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$RESULTS_DIR/exp5_ls_all_rep3_${TIMESTAMP}.csv"

echo "" | tee -a "$LOG"
echo "=== Exp5 Rep3 FULL RERUN at $(date) | Output: $OUTPUT_FILE ===" | tee -a "$LOG"

cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
    -d "$JCODEC_DIR" \
    -p jcodec \
    -m "$METHOD_FILE" \
    -o "$OUTPUT_FILE" \
    -h "$MAVEN_HOME" \
    -j \
    -in 100 \
    -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
    -ms 3123 \
    -is 3223 \
    -st 180 \
    -mt "qwen2.5-coder" \
    -mo 60 \
    >> "$LOG" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Exp5 Rep3 full rerun DONE: $OUTPUT_FILE" | tee -a "$LOG"
else
    echo "WARNING: Exp5 Rep3 full rerun exited with code $exit_code" | tee -a "$LOG"
fi
echo "Finished at $(date)" | tee -a "$LOG"
