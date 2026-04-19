#!/bin/bash
# Run Exp2 (UCB+Trad) and Exp4 (LS+Trad) on gson at 500 steps, 3 reps each.

set -e

PROJECT_DIR="/Users/""/repos/gin-rl"
GSON_DIR="/Users/""/repos/gson/gson"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/gson_top2.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_gson_top2_500steps"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home

NUM_REPETITIONS=3
NUM_STEPS=500

mkdir -p "$RESULTS_DIR"

echo "=============================================="  | tee -a "$LOG"
echo "gson 500-step experiments — $TIMESTAMP"         | tee -a "$LOG"
echo "Results: $RESULTS_DIR"                           | tee -a "$LOG"
echo "=============================================="  | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Exp2: UCB + Traditional (500 steps) ===" | tee -a "$LOG"

for rep in $(seq 1 $NUM_REPETITIONS); do
    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
    RL_LOG="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Rep $rep (seed=$SEED) ---" | tee -a "$LOG"
    cd "$GSON_DIR" && java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$GSON_DIR" \
        -p gson \
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
        -rllog "$RL_LOG" \
        >> "$LOG" 2>&1
    echo "Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== Exp4: LS + Traditional (500 steps) ===" | tee -a "$LOG"

for rep in $(seq 1 $NUM_REPETITIONS); do
    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp4_ls_trad_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Rep $rep (seed=$SEED) ---" | tee -a "$LOG"
    cd "$GSON_DIR" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$GSON_DIR" \
        -p gson \
        -m "$METHOD_FILE" \
        -o "$OUTPUT_FILE" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -ms $SEED \
        -is $((SEED + 100)) \
        >> "$LOG" 2>&1
    echo "Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== All gson 500-step experiments done at $(date) ===" | tee -a "$LOG"
