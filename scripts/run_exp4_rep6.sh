#!/bin/bash
PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
LOG="$PROJECT_DIR/experiment_run_bg.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="$RESULTS_DIR/exp4_ls_trad_rep6_${TIMESTAMP}.csv"
SEED=6123

echo "" | tee -a "$LOG"
echo "=== Exp4 Rep6 starting at $(date) | seed=$SEED ===" | tee -a "$LOG"
echo "Output: $OUTPUT_FILE" | tee -a "$LOG"

cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
    -d "$JCODEC_DIR" \
    -p jcodec \
    -m "$METHOD_FILE" \
    -o "$OUTPUT_FILE" \
    -h "$MAVEN_HOME" \
    -j \
    -in 100 \
    -et "STATEMENT,MATCHED_STATEMENT" \
    -ms $SEED \
    -is $((SEED + 100)) \
    >> "$LOG" 2>&1

exit_code=$?
if [ $exit_code -eq 0 ]; then
    echo "Exp4 Rep6 DONE: $OUTPUT_FILE" | tee -a "$LOG"
else
    echo "WARNING: Exp4 Rep6 exited with code $exit_code" | tee -a "$LOG"
fi
echo "Finished at $(date)" | tee -a "$LOG"
