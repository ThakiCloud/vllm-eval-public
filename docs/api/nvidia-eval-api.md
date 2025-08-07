# NVIDIA Eval API

The NVIDIA Eval API provides specialized evaluation capabilities for mathematical reasoning and coding tasks using industry-standard benchmarks. This API focuses on rigorous evaluation of large language models across different domains including competitive programming and mathematical problem-solving.

!!! info "Overview"

    NVIDIA Eval supports three main benchmark categories:

    - **LiveCodeBench**: Dynamic coding benchmark with recent problems
    - **AIME24/AIME25**: Mathematical reasoning benchmarks from American Invitational Mathematics Examination
    - **Docker Support**: Containerized execution for consistent environments

## Prerequisites

!!! warning "Requirements"

    Before using NVIDIA Eval, ensure you have:

    - A running VLLM server endpoint (e.g.,`http://localhost:8000/v1`)
    - Python environment with required dependencies
    - Docker installed (for containerized execution)
    - Sufficient computational resources for inference

## LiveCodeBench Evaluation

LiveCodeBench provides a dynamic evaluation platform for coding tasks with problems sourced from recent competitive programming contests, ensuring minimal data contamination.

!!! tip "About LiveCodeBench"

    LiveCodeBench is continuously updated with new problems, making it ideal for evaluating code generation capabilities without training data leakage concerns.

### Step-by-Step Process

#### 1. Dataset Preparation

First, download the LiveCodeBench dataset:

```bash
python download_livecodebench.py
```

!!! note "Dataset Location"

    The dataset will be saved to`data/livecodebench_problems.jsonl` and contains coding problems with test cases.

#### 2. Model Inference

Run inference against your model endpoint:

```bash
python inference.py \
    --api-base http://localhost:8000/v1 \
    --datapath data/livecodebench_problems.jsonl \
    --model-type opt125m \
    --output-folder "./results_livecodebench"
```

**Parameter Explanation:**

- `--api-base`: Your VLLM server endpoint
- `--datapath`: Path to the dataset file
- `--model-type`: Model identifier for logging
- `--output-folder`: Directory for storing inference results

#### 3. Evaluation

Evaluate the generated solutions:

```bash
python evaluate_livecodebench.py \
 --question-path data/livecodebench_problems.jsonl \
 --generation-path results_livecodebench/
```

!!! success "Expected Output"

    The evaluation will generate accuracy metrics, execution success rates, and detailed analysis of coding performance.

## AIME Mathematical Benchmarks

The American Invitational Mathematics Examination (AIME) benchmarks test advanced mathematical reasoning capabilities across algebra, geometry, number theory, and combinatorics.

!!! info "Benchmark Details"

    - **AIME24**: ~30 challenging mathematical problems from 2024
    - **AIME25**: ~15 problems from 2025
    - Both datasets require multi-step reasoning and exact numerical answers

### AIME24 Evaluation

#### 1. Model Inference

```bash
python inference.py \
    --api-base http://localhost:8000/v1 \
    --datapath data/aime24.jsonl \
    --model-type opt125m \
    --output-folder "./results_aime24"
```

#### 2. Evaluation

```bash
python evaluate_aime.py \
    --question-path data/aime24.jsonl \
    --generation-path results_aime24
```

### AIME25 Evaluation

#### 1. Model Inference

```bash
python inference.py \
    --api-base http://localhost:8000/v1 \
    --datapath data/aime25.jsonl \
    --model-type opt125m \
    --output-folder "./results_aime25"
```

#### 2. Evaluation

```bash
python evaluate_aime.py \
    --question-path data/aime25.jsonl \
    --generation-path results_aime25
```

!!! tip "Mathematical Evaluation"

    AIME evaluations use exact match scoring for numerical answers. The evaluation script handles various answer formats and provides detailed problem-by-problem analysis.

## Docker Deployment

For consistent execution environments and simplified deployment, use the Docker-based approach:

### Building the Image

```bash
docker build . -f docker/nvidia_eval.Dockerfile -t nvidia-benchmark:latest --no-cache
```

!!! warning "Build Requirements"

    The Docker build process requires significant resources and may take several minutes. Ensure you have adequate disk space and memory.

### Running Evaluations

```bash
docker run --rm \
  --network host \
  -v $(pwd)/results:/workspace/output \
  -e MODEL_ENDPOINT="http://localhost:8080/v1" \
  -e MODEL_NAME="facebook/opt-125m" \
  -e OUTPUT_DIR="run-001" \
  -e EVAL_TYPE="aime" \
  -e MAX_TOKENS="512" \
  nvidia-benchmark:latest
```

**Environment Variables:**

- `MODEL_ENDPOINT`: VLLM server endpoint URL
- `OUTPUT_DIR`: Container output directory
- `EVAL_TYPE`: Benchmark type (`aime`, `lcb`, `both`)
- `MAX_TOKENS`: Maximum output sequence length
- Volume mount maps local `output` directory to container workspace

!!! note "Network Configuration"

    The`--network host` flag enables the container to access the host's VLLM server. Adjust network settings based on your deployment architecture.

## Output Structure

After running evaluations, you'll find results organized as:

```
output/
├── results_livecodebench/     # LiveCodeBench inference results
├── results_aime24/            # AIME24 inference results
├── results_aime25/            # AIME25 inference results
├── evaluation_results.json    # Aggregated metrics
└── logs/                      # Detailed execution logs
```

!!! success "Next Steps"

    Use the generated results for model comparison, performance analysis, and integration with the broader VLLM evaluation pipeline.
