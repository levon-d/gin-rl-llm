#!/bin/bash

# Experiment 5: Local Search, Traditional + LLM Operators (no RL)
# Runs reps SEQUENTIALLY to avoid concurrent Ollama calls causing hangs/crashes.
# Baseline comparison for Exp 3 (UCB RL) — isolates benefit of RL over random LLM selection.
#
# Usage:  nohup ./run_exp5_localsearch_all.sh > /dev/null 2>&1 &
# Monitor: tail -f ~/repos/gin-rl/experiment_run_bg.log | grep --line-buffered -E "(Exp 5|done|WARNING|complete)"

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG="$PROJECT_DIR/experiment_run_bg.log"

NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60    # seconds per LLM call
REP_TIMEOUT=57600  # 16 hours per rep

mkdir -p "$RESULTS_DIR"

# Check Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "ERROR: Ollama not reachable at localhost:11434. Start Ollama first." | tee -a "$LOG"
    exit 1
fi

echo "" | tee -a "$LOG"
echo "Starting Experiment 5 (LocalSearch Traditional+LLM, sequential) at $(date) | Timestamp: $TIMESTAMP" | tee -a "$LOG"

run_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local output_file="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp 5 Rep $rep started (seed=$seed) ---" | tee -a "$LOG"

    cd "$JCODEC_DIR" && gtimeout $REP_TIMEOUT java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$JCODEC_DIR" \
        -p jcodec \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 124 ] || [ $exit_code -eq 143 ]; then
        echo "WARNING: Exp 5 Rep $rep timed out after ${REP_TIMEOUT}s" | tee -a "$LOG"
    else
        echo "Exp 5 Rep $rep done: $output_file" | tee -a "$LOG"
    fi
}

# Sequential — one rep at a time to avoid concurrent Ollama calls
for rep in 1 2 3 4 5; do
    run_rep $rep
done

echo "Experiment 5 complete at $(date)" | tee -a "$LOG"
