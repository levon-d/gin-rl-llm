#!/bin/bash
# Run reps 4 and 5 of gson Exp1 (Random), Exp2 (UCB+Trad), Exp4 (LS+Trad).
# Seeds: rep4=4123, rep5=5123

set -e

PROJECT_DIR="/Users/""/repos/gin-rl"
GSON_DIR="/Users/""/repos/gson/gson"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/gson_top2.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_gson_top2"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home

NUM_STEPS=100

mkdir -p "$RESULTS_DIR"

echo "=============================================="  | tee -a "$LOG"
echo "gson Exp1/Exp2/Exp4 reps 4+5 — $TIMESTAMP"     | tee -a "$LOG"
echo "Results: $RESULTS_DIR"                           | tee -a "$LOG"
echo "=============================================="  | tee -a "$LOG"

echo "" | tee -a "$LOG"
echo "=== Exp1: Random Sampling (reps 4-5) ===" | tee -a "$LOG"

for rep in 4 5; do
    SEED=$((123 + rep * 1000))
    OUTPUT_FILE="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"
    LOG_FILE="$RESULTS_DIR/exp1_log_rep${rep}_${TIMESTAMP}.txt"

    echo "--- Rep $rep (seed=$SEED) ---" | tee -a "$LOG"
    cd "$GSON_DIR" && java -cp "$GIN_JAR" gin.util.RandomSampler \
        -d "$GSON_DIR" \
        -p gson \
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
    echo "Rep $rep done: $OUTPUT_FILE" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== Exp2: UCB + Traditional (reps 4-5) ===" | tee -a "$LOG"

for rep in 4 5; do
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
echo "=== Exp4: LS + Traditional (reps 4-5) ===" | tee -a "$LOG"

for rep in 4 5; do
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
echo "=== All done at $(date) ===" | tee -a "$LOG"
