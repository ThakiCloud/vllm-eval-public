# Docker Standardization Guide

## Overview

This guide provides standardized Docker configurations for all VLLM evaluation frameworks. The standardization ensures consistent parameters, directory structure, and usage patterns across all evaluation containers.

## Key Standardizations

### 1. Base Configuration

| Aspect | Standardized Value |
|--------|-------------------|
| Base Image | `python:3.11-slim` |
| Working Directory | `/app` |
| User | `evaluser` |
| Python Environment | Unbuffered, no cache |

### 2. Directory Structure

All containers follow this standardized structure:

```
/app/
├── configs/
│   └── eval_config.json       # Framework configuration
├── eval/
│   └── <framework>/            # Framework-specific code
├── scripts/
│   └── standardize_*.py        # Result standardization scripts
├── results/                    # Evaluation results
├── parsed/                     # Parsed/processed results
└── cache/                      # Temporary cache
```

### 3. Environment Variables

#### Core Variables (All Frameworks)
```bash
EVAL_FRAMEWORK=<framework-name>         # Framework identifier
EVAL_CONFIG_PATH=/app/configs/eval_config.json
MODEL_ENDPOINT=http://localhost:8000/v1/completions
OUTPUT_DIR=/app/results
PARSED_DIR=/app/parsed
LOG_LEVEL=INFO
PYTHONPATH=/app
BACKEND_API=http://model-benchmark-backend-svc:8000
```

#### Evaluation Parameters
```bash
BATCH_SIZE=1                           # Batch size for processing
MAX_TOKENS=14000                       # Maximum tokens (varies by framework)
NUM_FEWSHOT=1                          # Few-shot examples
LIMIT=1                                # Limit for testing
```

#### Framework-Specific Variables

**NVIDIA Eval:**
```bash
EVAL_TYPE=both                         # aime|lcb|both
MAX_TOKENS=32768                       # Higher token limit
```

**VLLM Benchmark:**
```bash
NUM_PROMPTS=100                        # Number of prompts
REQUEST_RATE=1.0                       # Requests per second
MAX_CONCURRENCY=1                      # Concurrent requests
RANDOM_INPUT_LEN=512                   # Input length for random data
RANDOM_OUTPUT_LEN=128                  # Output length for random data
BACKEND=vllm                           # Backend type
DATASET_TYPE=random                    # Dataset type
```

#### Endpoint Conventions

- Default: use a single full URL in `MODEL_ENDPOINT` (for example: `http://localhost:8000/v1/completions`).
- vllm-benchmark: uses `MODEL_ENDPOINT` as the base URL plus an `ENDPOINT_PATH` (default: `/v1/chat/completions`). Override `ENDPOINT_PATH` if needed.
- nvidia-eval: expects `MODEL_ENDPOINT` to be the API base (for example: `http://localhost:8000/v1`). The toolkit scripts pass their own routes; no `ENDPOINT_PATH` is required.

### 4. Labels and Metadata

All containers include standardized labels:

```dockerfile
LABEL maintainer="VLLM Eval Team"
LABEL framework="<framework-name>"
LABEL version="1.1.0"
LABEL description="<framework-description>"
LABEL gpu.required="<true|false>"
```

## Usage Examples

### Evalchemy Framework

```bash
# Build
docker build -f docker/evalchemy.Dockerfile -t vllm-eval/evalchemy:latest .

# Run
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/parsed:/app/parsed \
  -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
  -e MODEL_NAME="qwen3-8b" \
  -e LOG_LEVEL="DEBUG" \
  vllm-eval/evalchemy:latest
```

### NVIDIA Eval Framework

```bash
# Build
docker build -f docker/nvidia-eval.Dockerfile -t vllm-eval/nvidia-eval:latest .

# Run AIME + LiveCodeBench
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/parsed:/app/parsed \
  -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1" \
  -e MODEL_NAME="qwen3-8b" \
  -e EVAL_TYPE="both" \
  -e MAX_TOKENS="32768" \
  vllm-eval/nvidia-eval:latest

# Run only AIME
docker run --rm \
  -v $(pwd)/results:/app/results \
  -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1" \
  -e MODEL_NAME="qwen3-8b" \
  -e EVAL_TYPE="aime" \
  vllm-eval/nvidia-eval:latest
```

### Standard Evalchemy Framework

```bash
# Build
docker build \
  -f docker/standard-evalchemy.Dockerfile \
  -t vllm-eval/standard-evalchemy:latest .

# Run
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/parsed:/app/parsed \
  -e MODEL_ENDPOINT="http://host.docker.internal:8000/v1/completions" \
  -e MODEL_NAME="qwen3-8b" \
  -e LOG_LEVEL="DEBUG" \
  vllm-eval/standard-evalchemy:latest
```

### VLLM Benchmark Framework

```bash
# Build
docker build -f docker/vllm-benchmark.Dockerfile -t vllm-eval/vllm-benchmark:latest .

# Run
docker run --rm \
  -v $(pwd)/results:/app/results \
  -v $(pwd)/parsed:/app/parsed \
  -e MODEL_ENDPOINT="http://host.docker.internal:8000" \
  -e MODEL_NAME="qwen3-8b" \
  -e NUM_PROMPTS="100" \
  -e REQUEST_RATE="2.0" \
  vllm-eval/vllm-benchmark:latest
```

## Common Parameters

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `MODEL_ENDPOINT` | API endpoint for the model | `http://localhost:8000/v1/completions` |
| `MODEL_NAME` | Name of the model to evaluate | `qwen3-8b` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARN, ERROR) |
| `BATCH_SIZE` | `1` | Batch size for processing |
| `MAX_TOKENS` | `14000` | Maximum tokens (varies by framework) |
| `OUTPUT_DIR` | `/app/results` | Results output directory |
| `PARSED_DIR` | `/app/parsed` | Parsed results directory |

### Volume Mounts

All containers support these standard volume mounts:

```bash
-v $(pwd)/results:/app/results     # Evaluation results
-v $(pwd)/parsed:/app/parsed       # Parsed results
-v $(pwd)/cache:/app/cache         # Cache directory (optional)
```

## Healthchecks

All containers include standardized healthchecks:

- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Start Period**: 5 seconds
- **Retries**: 3

## Security

All containers follow security best practices:

- Run as non-root user (`evaluser`)
- Minimal system packages
- No unnecessary privileges
- Clean package cache

## Migration from Original Dockerfiles

### Environment Variable Mapping

| Original | Standardized | Notes |
|----------|-------------|-------|
| `VLLM_MODEL_ENDPOINT` | `MODEL_ENDPOINT` | Consistent naming |
| `API_BASE` | `MODEL_ENDPOINT` | Unified endpoint variable |
| `VLLM_ENDPOINT` | `MODEL_ENDPOINT` | Single endpoint variable |
| Various output paths | `OUTPUT_DIR` | Standardized output |
| Various log levels | `LOG_LEVEL` | Consistent logging |

### Directory Structure Changes

| Original | Standardized | Impact |
|----------|-------------|--------|
| `/workspace` | `/app` | Consistent working directory |
| Various config paths | `/app/configs/eval_config.json` | Unified config location |
| Mixed result paths | `/app/results` | Standardized results |

## Testing

To test all standardized containers:

```bash
# Build all containers
make build-standardized

# Test with mock server
docker run -d --name mock-vllm -p 8000:8000 mock-vllm-server
docker run --rm --network host -e MODEL_ENDPOINT="http://localhost:8000/v1/completions" -e MODEL_NAME="test" vllm-eval/evalchemy:latest --validate
docker run --rm --network host -e MODEL_ENDPOINT="http://localhost:8000/v1" -e MODEL_NAME="test" -e EVAL_TYPE="aime" vllm-eval/nvidia-eval:latest
docker stop mock-vllm
```

## Benefits

1. **Consistency**: All containers use the same parameter patterns
2. **Predictability**: Users know what to expect across frameworks
3. **Maintainability**: Easier to update and maintain
4. **Documentation**: Clear usage patterns and examples
5. **Automation**: Easier to integrate into CI/CD pipelines
6. **Debugging**: Consistent logging and error handling