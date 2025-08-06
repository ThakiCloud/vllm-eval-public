# Evalchemy API

Evalchemy is a unified benchmark runner built on EleutherAI's lm-evaluation-harness, providing comprehensive evaluation capabilities for large language models. It supports both standard academic benchmarks and custom evaluation tasks with flexible API-based model integration.

!!! info "Evalchemy Overview"
    
    Evalchemy provides:
    
    - **Unified Benchmarking**: Single interface for multiple evaluation frameworks
    - **Standard Benchmarks**: ARC, HellaSwag, MMLU, Ko-MMLU, Ko-ARC support
    - **API Integration**: Compatible with VLLM and other serving frameworks
    - **Flexible Deployment**: Docker and script-based execution options

## Prerequisites

!!! warning "System Requirements"
    
    Before using Evalchemy, ensure you have:
    
    - Python 3.8+ environment
    - A running VLLM server endpoint
    - Docker (for containerized execution)
    - Sufficient computational resources for benchmark evaluation
    - Network connectivity between client and model server

## Execution Methods

Evalchemy supports two primary execution approaches, each optimized for different use cases:

### 1. Docker Execution (Recommended)

**Advantages:**

- Consistent execution environment
- Simplified dependency management  
- Easy integration with Kubernetes workflows
- Reproducible results across systems

### 2. Script Execution

**Advantages:**

- Direct system access for debugging
- Faster iteration during development
- Custom environment configuration
- Local filesystem integration

## Docker-Based Evaluation

### Building the Container

Create the Evalchemy Docker image:

```bash
docker build -f docker/standard_evalchemy.Dockerfile \
    -t standard-evalchemy:latest .
```

!!! tip "Image Optimization"
    
    The Docker build process includes optimized dependency installation and caching for faster subsequent builds.

### Container Execution

Run comprehensive benchmarks in a containerized environment:

```bash
docker run --rm \
    --network host \
    -v $(pwd)/results:/app/evalchemy-src/results \
    -e VLLM_MODEL_ENDPOINT="http://localhost:8080/v1/completions" \
    -e MODEL_NAME="Qwen/Qwen2-0.5B" \
    -e TOKENIZER="Qwen/Qwen2-0.5B" \
    standard-evalchemy:latest
```

!!! note "Network Configuration"

    `--network host` resolves MODEL ID and MODEL NAME resolution issues by providing direct access to the host network stack.

### Environment Variables Explained

**Model Configuration:**

- `VLLM_MODEL_ENDPOINT`: Complete API endpoint URL including path
- `MODEL_NAME`: HuggingFace model identifier
- `SERVED_MODEL_NAME`: Model name as configured in VLLM server
- `TOKENIZER`: Tokenizer specification for accurate token counting
- `TOKENIZER_BACKEND`: Backend implementation (`huggingface`, `tiktoken`)

**Evaluation Configuration:**

- `MODEL_CONFIG`: JSON configuration for API behavior and retries
- `EVALUATION_CONFIG`: Benchmark parameters including limits and output format

### Output Structure

After execution, results are organized in the following structure:

```bash
├── eval/
│   └── standard_evalchemy/
│       ├── parsed/          # Processed benchmark data
│       └── results/         # Evaluation outcomes and metrics
```

!!! success "Output Details"
    
    - **parsed/**: Contains preprocessed benchmark questions and expected answers
    - **results/**: Includes model responses, accuracy metrics, and detailed analysis

## Script-Based Evaluation

### Environment Setup

#### Install Core Dependencies

```bash
pip install -r requirements-dev.txt
```

#### Install Evalchemy Library

```bash
git clone https://github.com/ThakiCloud/evalchemy.git
cd evalchemy
pip install -e .
cd ..
```

!!! warning "Editable Installation"
    
    The `-e` flag installs Evalchemy in editable mode, allowing for local modifications and development.

### Running Evaluations

Execute benchmarks using the provided shell script:

```bash
./run_evalchemy.sh \
  --endpoint http://localhost:8000/v1/completions \
  --model-name "facebook/opt-125m" \
  --tokenizer "facebook/opt-125m" \
  --tokenizer-backend "huggingface" \
  --batch-size 1 \
  --run-id test_01
```

**Script Parameters:**

- `--endpoint`: API endpoint for model inference
- `--model-name`: Model identifier for evaluation context
- `--tokenizer`: Tokenizer specification for proper preprocessing
- `--tokenizer-backend`: Tokenization implementation choice
- `--batch-size`: Number of parallel requests (adjust based on server capacity)
- `--run-id`: Unique identifier for tracking evaluation runs

### Script Output Structure

Results are generated in the same directory structure:

```bash
├── eval/
│   └── standard_evalchemy/
│       ├── parsed/          # Benchmark preprocessing results
│       └── results/         # Evaluation metrics and analysis
```

## Advanced Configuration

### Custom Benchmark Selection

Modify evaluation parameters by editing configuration files:

```bash
# Edit benchmark selection
vim configs/evaluation_config.yaml

# Available benchmarks
benchmarks:
  - arc_easy
  - arc_challenge  
  - hellaswag
  - mmlu
  - ko_mmlu
  - ko_arc
```

### Performance Tuning

!!! tip "Optimization Tips"
    
    **For High-Throughput Evaluation:**

    - Increase `--batch-size` based on server capacity
    - Configure appropriate retry policies in `MODEL_CONFIG`
    - Monitor server resource utilization during evaluation
    
    **For Memory-Constrained Environments:**

    - Reduce batch size to minimize memory usage
    - Use streaming evaluation for large datasets
    - Configure appropriate timeouts to prevent hanging requests

### Multi-GPU Evaluation

For accelerated evaluation on multi-GPU systems:

```bash
docker run --rm \
    --gpus all \
    --network host \
    -e CUDA_VISIBLE_DEVICES="0,1,2,3" \
    -e VLLM_MODEL_ENDPOINT="http://localhost:8080/v1/completions" \
    # ... other environment variables
    standard-evalchemy:latest
```

## Benchmark Coverage

### Standard Academic Benchmarks

!!! info "Supported Benchmarks"
    
    **English Benchmarks:**

    - **ARC (Easy/Challenge)**: Science question answering
    - **HellaSwag**: Commonsense reasoning completion
    - **MMLU**: Massive multitask language understanding
    
    **Korean Benchmarks:**

    - **Ko-MMLU**: Korean multitask language understanding  
    - **Ko-ARC**: Korean science question answering

### Custom Benchmark Integration

Evalchemy supports custom benchmark integration:

```python
# Custom benchmark configuration
{
    "task": "custom_benchmark",
    "dataset_path": "/path/to/custom/data.jsonl",
    "metric": "exact_match",
    "few_shot": 5
}
```

## Result Analysis

### Metric Interpretation

!!! success "Understanding Results"
    
    **Key Metrics:**

    - **Accuracy**: Percentage of correctly answered questions
    - **F1 Score**: Harmonic mean of precision and recall
    - **Exact Match**: Strict equality comparison for answers
    - **BLEU Score**: Text similarity for generative tasks

### Comparative Analysis

Results include comparative analysis against baseline models:

```json
{
    "model": "Qwen/Qwen2-0.5B",
    "benchmark": "arc_easy",
    "accuracy": 0.785,
    "baseline_comparison": {
        "random_baseline": 0.25,
        "human_performance": 0.95,
        "relative_performance": 0.713
    }
}
```

## Integration with VLLM Eval Pipeline

### Automated Pipeline Integration

Evalchemy integrates seamlessly with the broader VLLM evaluation ecosystem:

```bash
# Integration with aggregation pipeline
python scripts/aggregate_metrics.py \
    --include-evalchemy \
    --results-dir eval/standard_evalchemy/results
```

!!! note "Pipeline Compatibility"
    
    Evalchemy results are automatically compatible with the VLLM evaluation aggregation system and ClickHouse analytics pipeline.

## Troubleshooting

### Common Issues

!!! warning "Troubleshooting Guide"
    
    **API Connection Issues:**

    - Verify VLLM server is running and accessible
    - Check endpoint URL format and network connectivity
    - Validate API authentication if required
    
    **Memory Issues:**

    - Reduce batch size for memory-constrained environments
    - Monitor system memory usage during evaluation
    - Consider using swap space for large evaluations
    
    **Performance Issues:**
    
    - Optimize batch size based on server capacity
    - Configure appropriate retry policies
    - Monitor server resource utilization

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
docker run --rm \
    --network host \
    -e DEBUG_MODE="true" \
    -e LOG_LEVEL="DEBUG" \
    # ... other environment variables
    standard-evalchemy:latest
```

## Next Steps

!!! success "Advanced Usage"
    
    After successful evaluation:
    
    - Analyze results using provided analysis scripts
    - Integrate with monitoring and alerting systems
    - Configure automated evaluation pipelines
    - Develop custom benchmarks for domain-specific evaluation
