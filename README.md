# gin-rl

Extension of the [GIN](https://github.com/gintool/gin) (Genetic Improvement in No time) framework with Reinforcement Learning-guided mutation operator selection, developed as part of a BSc Computer Science dissertation at UCL.

**Dissertation title:** *Reinforcement Learning for Adaptive Selection Between Traditional & LLM-Based Mutation Operators in Genetic Improvement*

For general GIN documentation see [README_GIN.md](README_GIN.md).

---

## System Manual

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Java (JDK) | 21 | `JAVA_HOME` must point to JDK 21 |
| Gradle (wrapper) | 8.0.2+ | Use `./gradlew` — no separate install needed |
| Maven | 3.9.x | Used internally by GIN to build/test target projects |
| Ollama | Latest | Required for Experiments 3 and 5 (LLM operators) only |

Set the Java home before building or running:
```bash
export JAVA_HOME=/Library/Java/JavaVirtualMachines/jdk-21.jdk/Contents/Home
```

**Ollama (LLM experiments only):**
```bash
ollama pull qwen2.5-coder:7b
ollama serve   # must be running on localhost:11434 during LLM experiments
```

---

### Building

```bash
./gradlew shadowJar
```

This produces a single fat JAR at `build/gin.jar`. All experiment scripts reference this path. Rebuild after any source changes.

---

### Repository Structure

```
gin-rl/
├── src/main/java/gin/
│   ├── edit/
│   │   ├── statement/      # CopyStatement, DeleteStatement, MoveStatement, ReplaceStatement, SwapStatement
│   │   ├── matched/        # MatchedCopy/Delete/Replace/SwapStatement
│   │   ├── modifynode/     # UnaryOperatorReplacement, BinaryOperatorReplacement, ReorderLogicalExpression
│   │   ├── line/           # Line-level edits (unused in dissertation experiments)
│   │   └── llm/            # LLMReplaceStatement, LLMMaskedStatement, Ollama4jLLMQuery
│   ├── rl/
│   │   ├── UCBSelector.java              # UCB1 bandit algorithm
│   │   ├── AbstractBanditSelector.java   # Shared bandit state and update logic
│   │   ├── OperatorSpace.java            # Operator set management (traditional / llm / all)
│   │   └── ExperimentLogger.java         # Per-step RL decision logging
│   └── util/
│       ├── RLLocalSearchRuntime.java     # RL-guided hill climbing (runtime fitness)
│       ├── LocalSearchRuntime.java       # Standard hill climbing (runtime fitness)
│       ├── RandomSampler.java            # Random patch baseline
│       └── GP.java                       # Base class: patch evaluation, CSV output
├── build/gin.jar                         # Built fat JAR (after ./gradlew shadowJar)
├── experiment_results/
│   ├── runtime_wang_top10/              # jcodec main results (100 steps)
│   ├── runtime_wang_top10_400steps/     # jcodec extended run (400 steps)
│   ├── runtime_junit4_top10/            # JUnit4 results
│   └── runtime_gson_top2/              # gson results
├── jcodec_wang_top10.csv               # Top 10 hot methods for jcodec
├── junit4_top10.csv                    # Top 10 hot methods for JUnit4
├── gson_top2.csv                       # Top 2 hot methods for gson
├── run_experiments.sh                  # Main experiment runner (jcodec)
└── run_gson_experiments.sh             # gson experiment runner
```

---

### Target Project Setup

Experiments run against external Java projects cloned separately. Each must be built at least once so Maven has its dependencies cached.

| Project | Repository | Branch/Tag |
|---|---|---|---|
| jcodec | github.com/jcodec/jcodec | master (7e52834) |
| JUnit4 | github.com/junit-team/junit4 | r4.13.2  |
| gson | github.com/google/gson | gson-parent-2.10.1  |

Build each project before running experiments:
```bash
cd /path/to/target-project
mvn test-compile -DskipTests
```

---

### Method Files

Each experiment requires a CSV file listing the target methods (hot methods from the Wang et al. profiler output):

| File | Project | Description |
|---|---|---|
| `jcodec_wang_top10.csv` | jcodec | Top 10 hot methods |
| `junit4_top10.csv` | JUnit4 | Top 10 hot methods |
| `gson_top2.csv` | gson | Top 2 hot methods |

Format (standard GIN HotMethod CSV): `ClassName,MethodName,Params,Tests`

---

### Running Experiments

#### jcodec (primary target)

```bash
./run_experiments.sh
```

Interactive menu:

| Choice | Experiment | Operators | Search |
|---|---|---|---|
| `1` | Random Sampling (baseline) | Traditional | Random |
| `2` | UCB + Traditional | Traditional | UCB (RL) |
| `3` | UCB + All (requires Ollama) | Traditional + LLM | UCB (RL) |
| `4` | Standard LS + Traditional | Traditional | Hill Climbing |
| `5` | Standard LS + All (requires Ollama) | Traditional + LLM | Hill Climbing |
| `t` | Experiments 1, 2, 4 (no LLM) | — | — |
| `a` | All experiments in sequence | — | — |

Results are written to `experiment_results/runtime_wang_top10/`.

#### gson

```bash
./run_gson_experiments.sh
```

Same menu structure. Results written to `experiment_results/runtime_gson_top2/`.

#### Extended 400-step run (jcodec, Experiment 3)

```bash
./run_exp3_400steps.sh
```

Results written to `experiment_results/runtime_wang_top10_400steps/`.

---

### Key Configuration Variables

All experiment scripts share these variables at the top of the file:

| Variable | Default | Description |
|---|---|---|
| `PROJECT_DIR` | `` | Root of this repository |
| `GIN_JAR` | `$PROJECT_DIR/build/gin.jar` | Path to the built fat JAR |
| `METHOD_FILE` | project-specific CSV | Target methods |
| `RESULTS_DIR` | `experiment_results/...` | Output directory |
| `MAVEN_HOME` | `/opt/homebrew/Cellar/maven/3.9.13/libexec` | Maven installation path |
| `JAVA_HOME` | JDK 21 path | Java version |
| `NUM_STEPS` | `100` | Search iterations per method |
| `NUM_REPETITIONS` | `3`–`5` | Independent repetitions |
| `LLM_MODEL_TYPE` | `qwen2.5-coder` | Ollama model name |
| `LLM_TIMEOUT` | `60` | LLM query timeout (seconds) |

Seeds are set deterministically: `seed = 123 + rep × 1000`.

---

### Output Format

**Main results CSV** (`exp{N}_{variant}_rep{R}_{timestamp}.csv`):

| Column | Description |
|---|---|
| `MethodID` | Target method identifier |
| `PatchIndex` | Patch number within the run |
| `Patch` | Edit sequence applied |
| `Compiled` | Whether the patch compiled |
| `AllTestsPassed` | Whether all tests passed |
| `WallClockTime(ms)` | Total wall-clock time for test execution |
| `Fitness` | Runtime fitness value |
| `Improvement` | Improvement over baseline (%) |

**RL log CSV** (`exp{N}_rl_log_rep{R}_{timestamp}.csv`, Experiments 2 and 3 only):

| Column | Description |
|---|---|
| `MethodID` | Target method |
| `Step` | Search step index |
| `Operator` | Operator selected by UCB |
| `Success` | Whether the patch compiled and passed tests |
| `ParentRuntime(ms)` | Runtime of the current best patch |
| `ChildRuntime(ms)` | Runtime of the newly generated patch |
| `Reward` | UCB reward signal (`parentRuntime / childRuntime`) |

---

### Running Tests

```bash
./gradlew test
```
