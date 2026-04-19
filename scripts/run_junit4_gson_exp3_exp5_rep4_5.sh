#!/bin/bash

# Run Exp3 + Exp5 reps 4 & 5 for JUnit4 and gson — sequentially.
# Order: JUnit4 Exp3 → JUnit4 Exp5 → gson Exp3 → gson Exp5
#
# Usage:
#   nohup ./run_junit4_gson_exp3_exp5_rep4_5.sh > /dev/null 2>&1 &
#
# Monitor:
#   tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(junit4|gson|Exp [35]|done|WARNING)"

PROJECT_DIR="/Users/""/repos/gin-rl"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
REP_TIMEOUT=57600  # 16 hours per rep

JUNIT4_DIR="/Users/""/repos/junit4"
JUNIT4_METHOD_FILE="$PROJECT_DIR/methods/methods/junit4_top10.csv"
JUNIT4_RESULTS="$PROJECT_DIR/experiment_results/runtime_junit4_top10"
JUNIT4_LLM_MODEL="qwen2.5-coder:1.5b"
JUNIT4_LLM_TIMEOUT=30

GSON_DIR="/Users/""/repos/gson/gson"
GSON_METHOD_FILE="$PROJECT_DIR/methods/methods/gson_top2.csv"
GSON_RESULTS="$PROJECT_DIR/experiment_results/runtime_gson_top2"
GSON_LLM_MODEL="qwen2.5-coder"
GSON_LLM_TIMEOUT=60

mkdir -p "$JUNIT4_RESULTS" "$GSON_RESULTS"

if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "========================================================" | tee -a "$LOG"
echo "JUnit4 + gson — Exp3 & Exp5 reps 4+5" | tee -a "$LOG"
echo "$(date) | Timestamp: $TIMESTAMP" | tee -a "$LOG"
echo "========================================================" | tee -a "$LOG"


for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$JUNIT4_RESULTS/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    rl_log_file="$JUNIT4_RESULTS/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- junit4 Exp3 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$JUNIT4_METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -rl ucb \
        -ops all \
        -rllog "$rl_log_file" \
        -mt "$JUNIT4_LLM_MODEL" \
        -mo $JUNIT4_LLM_TIMEOUT \
        >> "$LOG" 2>&1

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: junit4 Exp3 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "junit4 Exp3 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done


for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$JUNIT4_RESULTS/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- junit4 Exp5 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

    cd "$JUNIT4_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JUNIT4_DIR" \
        -p junit4 \
        -m "$JUNIT4_METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -mt "$JUNIT4_LLM_MODEL" \
        -mo $JUNIT4_LLM_TIMEOUT \
        >> "$LOG" 2>&1

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: junit4 Exp5 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "junit4 Exp5 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done

echo "junit4 Exp3+Exp5 reps 4+5 complete at $(date)" | tee -a "$LOG"


export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home

for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$GSON_RESULTS/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
    rl_log_file="$GSON_RESULTS/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"

    echo "--- gson Exp3 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

    cd "$GSON_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.RLLocalSearchRuntime \
        -d "$GSON_DIR" \
        -p gson \
        -m "$GSON_METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT" \
        -ms $seed \
        -is $((seed + 100)) \
        -rl ucb \
        -ops all \
        -rllog "$rl_log_file" \
        -mt "$GSON_LLM_MODEL" \
        -mo $GSON_LLM_TIMEOUT \
        >> "$LOG" 2>&1

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: gson Exp3 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "gson Exp3 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done


for rep in 4 5; do
    seed=$((123 + rep * 1000))
    output_file="$GSON_RESULTS/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- gson Exp5 Rep $rep started (seed=$seed) at $(date) ---" | tee -a "$LOG"

    cd "$GSON_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$GSON_DIR" \
        -p gson \
        -m "$GSON_METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -st 180 \
        -mt "$GSON_LLM_MODEL" \
        -mo $GSON_LLM_TIMEOUT \
        >> "$LOG" 2>&1

    exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: gson Exp5 Rep $rep timed out" | tee -a "$LOG"
    else
        echo "gson Exp5 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
done

echo "gson Exp3+Exp5 reps 4+5 complete at $(date)" | tee -a "$LOG"
echo "========================================================" | tee -a "$LOG"
echo "All done at $(date)" | tee -a "$LOG"
echo "========================================================" | tee -a "$LOG"
