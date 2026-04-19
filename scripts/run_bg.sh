#!/bin/bash

# Background runner for Experiments 1, 2, and 3
# Usage: ./run_bg.sh
# Monitor: tail -f experiment_run_bg.log

set -e

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

mkdir -p "$RESULTS_DIR"

echo "Starting experiments at $(date)" | tee "$LOG"
echo "Results dir: $RESULTS_DIR" | tee -a "$LOG"
echo "Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "" | tee -a "$LOG"

echo "=== EXPERIMENT 1: Random Sampling ===" | tee -a "$LOG"

for rep in $(seq 1 $NUM_REPETITIONS); do
    echo "--- Exp 1, Rep $rep/$NUM_REPETITIONS ($(date)) ---" | tee -a "$LOG"

    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"

    cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.RandomSampler \
        -d "$JCODEC_DIR" \
        -p jcodec \
        -m "$METHOD_FILE" \
        -o "$OUTPUT_FILE" \
        -h "$MAVEN_HOME" \
        -j \
        -pn $NUM_STEPS \
        -ps 1 \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -rp $SEED \
        -rm $((SEED + 100)) \
        >> "$LOG" 2>&1

    echo "Exp 1 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"

echo "=== EXPERIMENT 2: UCB Local Search (Traditional) ===" | tee -a "$LOG"

for rep in $(seq 1 $NUM_REPETITIONS); do
    echo "--- Exp 2, Rep $rep/$NUM_REPETITIONS ($(date)) ---" | tee -a "$LOG"

    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
    RL_LOG_FILE="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"

    cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
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
        -ops traditional \
        -rllog "$RL_LOG_FILE" \
        >> "$LOG" 2>&1

    echo "Exp 2 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"

echo "=== EXPERIMENT 3: UCB Local Search (Traditional + LLM: $LLM_MODEL) ===" | tee -a "$LOG"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

for rep in $(seq 1 $NUM_REPETITIONS); do
    echo "--- Exp 3, Rep $rep/$NUM_REPETITIONS ($(date)) ---" | tee -a "$LOG"

    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    RL_LOG_FILE="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    cd "$JCODEC_DIR" && java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
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

    echo "Exp 3 Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "All experiments complete at $(date)" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
