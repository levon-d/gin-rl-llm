#!/bin/bash

set -e

PROJECT_DIR="/Users/""/repos/gin-rl"
GSON_DIR="/Users/""/repos/gson/gson"
GIN_JAR="$PROJECT_DIR/build/gin.jar"
METHOD_FILE="$PROJECT_DIR/methods/gson_top2.csv"
RESULTS_DIR="$PROJECT_DIR/experiment_results/runtime_gson_top2"
MAVEN_HOME="/opt/homebrew/Cellar/maven/3.9.13/libexec"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# gson requires JDK [17,22) — use JDK 21
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home

NUM_REPETITIONS=3
NUM_STEPS=100

LLM_MODEL_TYPE="qwen2.5-coder"
LLM_TIMEOUT=60

mkdir -p "$RESULTS_DIR"

echo "=============================================="
echo "GIN-RL Experiment Runner — gson"
echo "=============================================="
echo "Timestamp:         $TIMESTAMP"
echo "Repetitions:       $NUM_REPETITIONS"
echo "Steps per method:  $NUM_STEPS"
echo "Results dir:       $RESULTS_DIR"
echo "Method file:       $METHOD_FILE"
echo "JAVA_HOME:         $JAVA_HOME"
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

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp1_random_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp1_log_rep${rep}_${TIMESTAMP}.txt"

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

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp2_ucb_trad_rep${rep}_${TIMESTAMP}.csv"
        RL_LOG_FILE="$RESULTS_DIR/exp2_rl_log_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp2_log_rep${rep}_${TIMESTAMP}.txt"

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
            -ops all \
            -rllog "$RL_LOG_FILE" \
            -mt "$LLM_MODEL_TYPE" \
            -mo $LLM_TIMEOUT \
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
        echo "RL log saved to:  $RL_LOG_FILE"
    done
}

# Experiment 4: Standard Local Search (Traditional Operators)
run_experiment4() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT 4: Standard Local Search"
    echo "(Traditional Operators Only)"
    echo "=============================================="

    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp4_ls_trad_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp4_log_rep${rep}_${TIMESTAMP}.txt"

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
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
    done
}

# Experiment 5: Standard Local Search (All Operators including LLM)
run_experiment5() {
    echo ""
    echo "=============================================="
    echo "EXPERIMENT 5: Standard Local Search"
    echo "(All Operators including LLM)"
    echo "=============================================="

    if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "WARNING: Ollama not reachable at localhost:11434"
        echo "Start Ollama before running this experiment."
        echo "Skipping Experiment 5."
        return 1
    fi

    # Run reps sequentially to avoid concurrent Ollama calls hanging
    for rep in $(seq 1 $NUM_REPETITIONS); do
        echo ""
        echo "--- Repetition $rep/$NUM_REPETITIONS ---"

        SEED=$((123 + rep * 1000))
        OUTPUT_FILE="$RESULTS_DIR/exp5_ls_all_rep${rep}_${TIMESTAMP}.csv"
        LOG_FILE="$RESULTS_DIR/exp5_log_rep${rep}_${TIMESTAMP}.txt"

        cd "$GSON_DIR" && java -cp "$GIN_JAR" gin.util.LocalSearchRuntime \
            -d "$GSON_DIR" \
            -p gson \
            -m "$METHOD_FILE" \
            -o "$OUTPUT_FILE" \
            -h "$MAVEN_HOME" \
            -j \
            -in $NUM_STEPS \
            -et "STATEMENT,MATCHED_STATEMENT,gin.edit.llm.LLMReplaceStatement,gin.edit.llm.LLMMaskedStatement" \
            -ms $SEED \
            -is $((SEED + 100)) \
            -st 180 \
            -mt "$LLM_MODEL_TYPE" \
            -mo $LLM_TIMEOUT \
            2>&1 | tee "$LOG_FILE"

        echo "Results saved to: $OUTPUT_FILE"
    done
}

echo "Select experiment to run:"
echo ""
echo "  1) Experiment 1: Random Sampling (baseline)"
echo "  2) Experiment 2: UCB Local Search (traditional operators)"
echo "  3) Experiment 3: UCB Local Search (traditional + LLM operators)"
echo "  4) Experiment 4: Standard LS (traditional operators)"
echo "  5) Experiment 5: Standard LS (traditional + LLM operators)"
echo ""
echo "  t) Experiments 1, 2, 4 (no LLM)"
echo "  a) All experiments in sequence (1 -> 2 -> 3 -> 4 -> 5)"
echo ""
read -p "Enter choice [1/2/3/4/5/t/a]: " choice

case $choice in
    1) run_experiment1 ;;
    2) run_experiment2 ;;
    3) run_experiment3 ;;
    4) run_experiment4 ;;
    5) run_experiment5 ;;
    t|T)
        run_experiment1
        run_experiment2
        run_experiment4
        ;;
    a|A)
        run_experiment1
        run_experiment2
        run_experiment3
        run_experiment4
        run_experiment5
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
ls -la "$RESULTS_DIR"/*.csv 2>/dev/null | tail -20 || echo "No CSV files yet"
