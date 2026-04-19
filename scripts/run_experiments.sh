#!/bin/bash

set -e

PROJECT_DIR="/Users/""/repos/gin-rl"
JCODEC_DIR="/Users/""/repos/jcodec"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/jcodec_wang_top10.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

NUM_REPETITIONS=3
NUM_STEPS=100  # Number of search steps per method

LLM_MODEL_TYPE="qwen2.5-coder"
LLM_TIMEOUT=60

mkdir -p "$RESULTS_DIR"

echo "=============================================="
echo "GIN-RL Experiment Runner"
echo "=============================================="
echo "Timestamp:         $TIMESTAMP"
echo "Repetitions:       $NUM_REPETITIONS"
echo "Steps per method:  $NUM_STEPS"
echo "Results dir:       $RESULTS_DIR"
echo "Method file:       $METHOD_FILE"
echo "LLM Model:         $LLM_MODEL_TYPE (via Ollama)"
echo ""

if [ ! -f "$GIN_JAR" ]; then
    echo "ERROR: GIN JAR not found at $GIN_JAR"
    echo "Run: ./gradlew shadowJar"
    exit 1
fi

if [ ! -f "$METHOD_FILE" ]; then
    echo "ERROR: Method file not found at $METHOD_FILE"
    exit 1
fi

# Experiment 1: Random Sampling (Baseline)
run_experiment1() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT 1: Random Sampling (Baseline)"
    echo "=============================================="
    echo ""

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp1_log_rep${rep}_${TIMESTAMP}.txt"

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
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
    done
}

# Experiment 2: UCB Local Search (Traditional Operators)
run_experiment2() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT 2: UCB Local Search"
    echo "(Traditional Operators Only)"
    echo "=============================================="
    echo ""

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
        RL_LOG_FILE="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp2_log_rep${rep}_${TIMESTAMP}.txt"

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
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
        echo "RL log saved to:  $RL_LOG_FILE"
    done
}

# Experiment 3: UCB Local Search (All Operators including LLM)
run_experiment3() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT 3: UCB Local Search"
    echo "(All Operators including LLM)"
    echo "=============================================="
    echo ""

    # Check Ollama is running
    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "WARNING: Ollama not reachable at localhost:11434"
        echo "Start Ollama before running this experiment."
        echo "Skipping Experiment 3."
        return 1
    fi

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp3_ucb_all_rep${rep}_${TIMESTAMP}.csv"
        RL_LOG_FILE="$RESULTS_DIR/exp3_rl_log_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp3_log_rep${rep}_${TIMESTAMP}.txt"

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
            -mt "$LLM_MODEL_TYPE" \
            -mo $LLM_TIMEOUT \
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
        echo "RL log saved to:  $RL_LOG_FILE"
    done
}

show_info() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT INFORMATION"
    echo "=============================================="
    echo ""
    echo "Target: Top 10 hot methods from Wang et al. profiler output"
    echo ""
    cat "$METHOD_FILE" | awk -F',' 'NR>1 {print NR-1". "$3}' | head -10
    echo ""
    echo "Operators:"
    echo "  Traditional: DeleteStatement, CopyStatement, ReplaceStatement,"
    echo "               SwapStatement, MoveStatement (statement + matched)"
    echo "               + BinaryOperatorReplacement, UnaryOperatorReplacement"
    echo "  LLM (Exp 3): LLMMaskedStatement, LLMReplaceStatement"
    echo ""
    echo "Time estimates (approximate, 10 methods x $NUM_STEPS steps x $NUM_REPETITIONS reps):"
    echo "  Exp 1 (Random):       ~1-2 hours"
    echo "  Exp 2 (UCB Trad):     ~2-4 hours"
    echo "  Exp 3 (UCB+LLM):      ~4-8 hours (LLM calls are slower)"
    echo ""
}

echo "Select experiment to run:"
echo ""
echo "  1) Experiment 1: Random Sampling (baseline)"
echo "  2) Experiment 2: UCB Local Search (traditional operators)"
echo "  3) Experiment 3: UCB Local Search (traditional + LLM operators)"
echo ""
echo "  a) All experiments in sequence (1 -> 2 -> 3)"
echo "  t) Experiments 1 and 2 only (no LLM)"
echo "  i) Show experiment information"
echo ""
read -p "Enter choice [1/2/3/a/t/i]: " choice

case $choice in
    1)
        run_experiment1
        ;;
    2)
        run_experiment2
        ;;
    3)
        run_experiment3
        ;;
    a|A)
        run_experiment1
        run_experiment2
        run_experiment3
        ;;
    t|T)
        run_experiment1
        run_experiment2
        ;;
    i|I)
        show_info
        exit 0
        ;;
    *)
        echo "Invalid choice. Exiting."
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "Experiments Complete!"
echo "=============================================="
echo "Results saved to: $RESULTS_DIR"
echo ""
echo "Output files:"
ls -la "$RESULTS_DIR"/*.csv 2>/dev/null | tail -20 || echo "No CSV files yet"
echo ""
echo "To analyse results, check:"
echo "  - exp*_output.csv:  Patch evaluations (runtime, improvements)"
echo "  - exp*_rl_log.csv:  RL decisions (operator selections, rewards)"
echo "  - exp*_log.txt:     Full execution logs"
