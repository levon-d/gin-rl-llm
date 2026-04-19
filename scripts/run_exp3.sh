#!/bin/bash

# Experiment 3 only: UCB Local Search (Traditional + LLM operators)
# Usage: ./run_exp3.sh
# Monitor: tail -f experiment_run_bg.log | grep -E "(Exp 3|done|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_REPETITIONS=5
NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60  # seconds per LLM call
REP_TIMEOUT=3600  # max seconds per rep (1 hour) before killing and moving on

mkdir -p "$RESULTS_DIR"

echo "Starting Experiment 3 at $(date)" | tee -a "$LOG"
echo "LLM Model: $LLM_MODEL" | tee -a "$LOG"
echo "Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "" | tee -a "$LOG"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "=== EXPERIMENT 3: UCB Local Search (Traditional + LLM: $LLM_MODEL) ===" | tee -a "$LOG"

for rep in $(seq 1 $NUM_REPETITIONS); do
    echo "--- Exp 3, Rep $rep/$NUM_REPETITIONS ($(date)) ---" | tee -a "$LOG"

    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    RL_LOG_FILE="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

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
        echo "WARNING: Exp 3 Rep $rep timed out after ${REP_TIMEOUT}s — moving to next rep" | tee -a "$LOG"
    else
        echo "Exp 3 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
    fi
done

echo "" | tee -a "$LOG"
echo "Experiment 3 complete at $(date)" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
