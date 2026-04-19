#!/bin/bash

# JUnit4 Experiment 1 RERUN: Random Sampling with -pn 1000 (100 per method)
#
# Usage:  nohup ./run_junit4_exp1_rerun.sh > /dev/null 2>&1 &

PROJECT_DIR="/Users/""/repos/gin-rl"
JUNIT4_DIR="/Users/""/repos/junit4"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/junit4_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_junit4_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_PATCHES=1000
REP_TIMEOUT=28800

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "=== Starting JUnit4 Exp1 RERUN (pn=1000) at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"

run_exp1_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"

    echo "--- JUnit4 Exp1 Rep $rep started (seed=$seed, pn=1000) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RandomSampler \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -pn $NUM_PATCHES \
        -ps 1 \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -rp $seed \
        -rm $((seed + 100)) \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: JUnit4 Exp1 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "JUnit4 Exp1 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

run_exp1_rep 1 &
run_exp1_rep 2 &
run_exp1_rep 3 &
wait

run_exp1_rep 4 &
run_exp1_rep 5 &
wait

echo "=== JUnit4 Exp1 RERUN complete at $(date) ===" | tee -a "$LOG"
