#!/bin/bash

# Complete jcodec Exp3 (UCB+LLM) and Exp5 (LS+LLM)
#
# Step 1: Exp3 Rep1 completion — run only the 2 missing methods (resample, getPlaneWidth)
#         and append to the existing Rep1 CSV.
# Step 2: Exp3 Rep2 + Rep3 — fresh full runs (3 reps total including existing Rep1)
# Step 3: Exp5 Rep1 + Rep2 + Rep3 — fresh full runs
#
# Usage:  nohup ./run_jcodec_exp3_exp5_complete.sh > /dev/null 2>&1 &
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp [35]|Rep|done|WARNING|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
MISSING_FILE="$PROJECT_DIR/methods/jcodec_exp3_rep1_missing.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60
REP_TIMEOUT=32400   # 9 hours per full rep (safe for 10 methods with LLM)
SHORT_TIMEOUT=7200  # 2 hours for the 2-method Rep1 completion

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "=== jcodec Exp3+Exp5 completion run at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"
echo "LLM: $LLM_MODEL | Steps: $NUM_STEPS | LLM timeout: ${LLM_TIMEOUT}s" | tee -a "$LOG"

# Check Ollama
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434." | tee -a "$LOG"
    exit 1
fi

EXP3_REP1_FILE="$RESULTS_DIR/exp3_ucb_all_rep1_20260316_230008.csv"
EXP3_REP1_COMPLETION="$RESULTS_DIR/exp3_ucb_all_rep1_completion_${TIMESTAMP}.csv"
EXP3_REP1_RLLOG="$RESULTS_DIR/exp3_rl_log_rep1_completion_${TIMESTAMP}.csv"

echo "" | tee -a "$LOG"
echo "--- Exp3 Rep1 completion: running resample + getPlaneWidth ($(date)) ---" | tee -a "$LOG"

SEED=1123
cd "$JCODEC_DIR" && gtimeout $SHORT_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
    -d "$JCODEC_DIR" \
    -p jcodec \
    -m "$MISSING_FILE" \
    -o "$EXP3_REP1_COMPLETION" \
    -h "$MAVEN_HOME" \
    -j \
    -in $NUM_STEPS \
    -et "STATEMENT,MATCHED_STATEMENT" \
    -ms $SEED \
    -is $((SEED + 100)) \
    -rl ucb \
    -ops all \
    -rllog "$EXP3_REP1_RLLOG" \
    -mt "$LLM_MODEL" \
    -mo $LLM_TIMEOUT \
    >> "$LOG" 2>&1

EXIT_CODE=$?
if [ $EXIT_CODE -eq 124 ] || [ $EXIT_CODE -eq 143 ]; then
    echo "WARNING: Exp3 Rep1 completion timed out" | tee -a "$LOG"
else
    echo "Exp3 Rep1 completion done: $EXP3_REP1_COMPLETION" | tee -a "$LOG"
fi

# Append results (skip header) to the existing Rep1 CSV
if [ -f "$EXP3_REP1_COMPLETION" ]; then
    ROWS_BEFORE=$(grep -c '^"' "$EXP3_REP1_FILE" 2>/dev/null || echo 0)
    tail -n +2 "$EXP3_REP1_COMPLETION" >> "$EXP3_REP1_FILE"
    ROWS_AFTER=$(grep -c '^"' "$EXP3_REP1_FILE" 2>/dev/null || echo 0)
    echo "Appended to Rep1: $ROWS_BEFORE -> $ROWS_AFTER valid rows" | tee -a "$LOG"
fi

echo "" | tee -a "$LOG"
echo "=== EXPERIMENT 3: UCB + All (Trad+LLM) — Rep2 + Rep3 ===" | tee -a "$LOG"

for rep in 2 3; do
    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    RL_LOG_FILE="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp3 Rep $rep (seed=$SEED, $(date)) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$JCODEC_DIR" \
        -p jcodec \
        -m "$METHOD_FILE" \
        -o "$OUTPUT_FILE" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -ms $SEED \
        -is $((SEED + 100)) \
        -rl ucb \
        -ops all \
        -rllog "$RL_LOG_FILE" \
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ] || [ $EXIT_CODE -eq 143 ]; then
        echo "WARNING: Exp3 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp3 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
    fi
done

echo "" | tee -a "$LOG"
echo "=== EXPERIMENT 5: Standard LS + All (Trad+LLM) — 3 reps ===" | tee -a "$LOG"

for rep in 1 2 3; do
    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp5 Rep $rep (seed=$SEED, $(date)) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
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
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 124 ] || [ $EXIT_CODE -eq 143 ]; then
        echo "WARNING: Exp5 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp5 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
    fi
done

echo "" | tee -a "$LOG"
echo "=== jcodec Exp3+Exp5 complete at $(date) ===" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
