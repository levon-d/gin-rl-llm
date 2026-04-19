#!/bin/bash

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_remaining3.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
LOG="$PROJECT_DIR/experiment_run_bg.log"
SEED=1123
REP1_FILE="$RESULTS_DIR/exp5_ls_all_rep1_20260323_140041.csv"
TEMP_FILE="$RESULTS_DIR/exp5_rep1_remaining_temp.csv"

echo "" | tee -a "$LOG"
echo "Starting Exp 5 Rep 1 remaining (3 methods) at $(date)" | tee -a "$LOG"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable." | tee -a "$LOG"
    exit 1
fi

cd "$JCODEC_DIR" && gtimeout 57600 java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
    -d "$JCODEC_DIR" \
    -p jcodec \
    -m "$METHOD_FILE" \
    -o "$TEMP_FILE" \
    -h "$MAVEN_HOME" \
    -j \
    -in 100 \
    -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
    -ms $SEED \
    -is $((SEED + 100)) \
    -mt "qwen2.5-coder" \
    -mo 60 \
    >> "$LOG" 2>&1

exit_code=$?
if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
    echo "WARNING: timed out" | tee -a "$LOG"
else
    echo "Exp 5 Rep 1 remaining done." | tee -a "$LOG"
fi

if [ -f "$TEMP_FILE" ]; then
    tail -n +2 "$TEMP_FILE" >> "$REP1_FILE"
    rm "$TEMP_FILE"
    echo "Appended to: $REP1_FILE" | tee -a "$LOG"
fi
