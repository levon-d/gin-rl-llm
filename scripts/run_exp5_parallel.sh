#!/bin/bash
# Exp5: Standard LS + All operators (Trad + LLM) — 3 reps sequentially
# Runs one rep at a time to avoid concurrent Ollama calls which cause hangs.
# Per-step timeout (180s) now built into LocalSearchSimple to prevent LLM hangs.
#
# Usage:  nohup ./run_exp5_parallel.sh > /dev/null 2>&1 &
# Monitor: tail -f experiment_run_bg.log | grep -E "(Exp5|Rep|done|WARNING|timed out)"

PROJECT_DIR="/Users/""/repos/gin-rl"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_wang_top10"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
LOG="$PROJECT_DIR/experiment_run_bg.log"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

NUM_STEPS=100
LLM_MODEL="qwen2.5-coder"
LLM_TIMEOUT=60
STEP_TIMEOUT=180   # per-step timeout (seconds) — kills hung LLM/test calls

mkdir -p "$RESULTS_DIR"

echo "" | tee -a "$LOG"
echo "=== Exp5 sequential run at $(date) | Timestamp: $TIMESTAMP ===" | tee -a "$LOG"
echo "Steps: $NUM_STEPS | LLM timeout: ${LLM_TIMEOUT}s | Step timeout: ${STEP_TIMEOUT}s" | tee -a "$LOG"

run_rep() {
    local rep=$1
    local seed=$((123 + rep * 1000))
    local jcodec_dir="/Users/""/repos/jcodec_exp5_rep${rep}"
    local output_file="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"

    echo "--- Exp5 Rep $rep starting (seed=$seed, dir=$jcodec_dir, $(date)) ---" | tee -a "$LOG"

    cd "$jcodec_dir" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
        -d "$jcodec_dir" \
        -p jcodec \
        -m "$METHOD_FILE" \
        -o "$output_file" \
        -h "$MAVEN_HOME" \
        -j \
        -in $NUM_STEPS \
        -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
        -ms $seed \
        -is $((seed + 100)) \
        -st $STEP_TIMEOUT \
        -mt "$LLM_MODEL" \
        -mo $LLM_TIMEOUT \
        >> "$LOG" 2>&1

    local exit_code=$?
    if [ $exit_code -eq 0 ]; then
        echo "Exp5 Rep $rep done: $output_file" | tee -a "$LOG"
    else
        echo "WARNING: Exp5 Rep $rep exited with code $exit_code" | tee -a "$LOG"
    fi
}

# Run reps sequentially — one Ollama call at a time to avoid concurrent hangs
for rep in 1 2 3; do
    run_rep $rep
    echo "Rep $rep finished at $(date)" | tee -a "$LOG"
done

echo "" | tee -a "$LOG"
echo "=== Exp5 all reps complete at $(date) ===" | tee -a "$LOG"
echo "Results in: $RESULTS_DIR" | tee -a "$LOG"
