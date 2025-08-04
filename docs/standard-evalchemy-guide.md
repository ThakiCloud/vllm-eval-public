# Standard Evalchemy Evaluation Guide

This guide explains how to run standard evalchemy evaluation and troubleshoot common issues.

## Quick Start

# 1. Build the Docker image

docker build -f docker/standard_evalchemy.Dockerfile \
 -t standard-evalchemy:latest .

# 3. Run evaluation

docker run --rm \
 --network host \
 -v $(pwd)/results:/app/evalchemy-src/results \
 -e VLLM_MODEL_ENDPOINT="http://localhost:8080/v1/completions" \
 -e MODEL_NAME="Qwen/Qwen2-0.5B" \
 -e SERVED_MODEL_NAME="qwen2-0.5b" \
 -e TOKENIZER="Qwen/Qwen2-0.5B" \
 -e TOKENIZER_BACKEND="huggingface" \
 -e MODEL_CONFIG='{"model_type": "curator", "api_config": {"max_retries": 3, "retry_delay": 5.0}}' \
 -e EVALUATION_CONFIG='{"limit": 100, "output_format": "json", "log_samples": true, "max_tokens": 2000}' \
 standard-evalchemy:latest

## Common Issues and Solutions

### 1. "Model endpoint is not valid or model ID missing"

This error occurs when:

- The container can't connect to VLLM server
- Required configuration is missing
- Model information is not properly set

**Solution**:

1. Add `--network host` to Docker run command
2. Provide all required environment variables:
   - `MODEL_NAME`
   - `SERVED_MODEL_NAME`
   - `TOKENIZER`
   - `MODEL_CONFIG`
   - `EVALUATION_CONFIG`

### 2. "Missing configuration section: .model_config"

This error occurs when model configuration is not provided.

**Solution**:
Add MODEL_CONFIG environment variable:

```bash
-e MODEL_CONFIG='{"model_type": "curator", "api_config": {"max_retries": 3, "retry_delay": 5.0}}'
```

### 3. "Missing configuration section: .evaluation_config"

This error occurs when evaluation configuration is not provided.

**Solution**:
Add EVALUATION_CONFIG environment variable:

```bash
-e EVALUATION_CONFIG='{"limit": 100, "output_format": "json", "log_samples": true, "max_tokens": 2000}'
```

## Configuration Options

### Model Configuration

```json
{
  "model_type": "curator",
  "api_config": {
    "max_retries": 3,
    "retry_delay": 5.0
  }
}
```

### Evaluation Configuration

```json
{
  "limit": 100,
  "output_format": "json",
  "log_samples": true,
  "max_tokens": 2000
}
```

## Available Benchmarks

The standard evalchemy includes several Arabic language benchmarks:

1. **hellaswag_ar**: Tests commonsense reasoning
2. **piqa_ar**: Physical interaction reasoning
3. **arabicmmlu**: Multi-task language understanding
4. **aexams**: Arabic exams benchmark
5. **copa_ar**: Choice of plausible alternatives

## Results Structure

After running the evaluation, results will be available in:

```
results/
└── {run_id}/
    ├── evalchemy_{run_id}.log              # Execution log
    ├── {benchmark}_results.json            # Results for each benchmark
    └── {benchmark}/                        # Detailed benchmark data
```

## Interpreting Results

Results are provided in JSON format with the following metrics:

- `acc`: Accuracy score
- `acc_stderr`: Standard error of accuracy
- `acc_norm`: Normalized accuracy (if applicable)

Example result structure:

```json
{
  "hellaswag_ar": {
    "acc,none": 0.29,
    "acc_stderr,none": 0.045604802157206845,
    "acc_norm,none": 0.29,
    "acc_norm_stderr,none": 0.045604802157206845
  }
}
```

## Best Practices

1. Always use `--network host` when running locally
2. Provide all required environment variables
3. Create results directory before running
4. Check VLLM server accessibility before running evaluation
5. Monitor the evaluation logs for progress

## Troubleshooting Steps

1. Verify VLLM server is running:

```bash
curl http://localhost:8080/v1/models
```

2. Check model endpoint:

```bash
curl -X POST http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"/data/local_models/finetune-qwen2-0-5b", "prompt": "Hello", "max_tokens": 10}'
```

3. Verify directory permissions:

```bash
ls -l results/
```

4. Check container logs:

```bash
docker logs <container_id>
```

## Notes

- The backend service warnings (`model-benchmark-backend-svc`) can be ignored if you're not using the backend service
- Results are saved both in raw format and standardized format
- Each benchmark run gets a unique run ID based on timestamp
