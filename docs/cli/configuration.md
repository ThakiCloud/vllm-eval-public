# Configuration Guide

The VLLM Evaluation CLI uses TOML-based configuration files to manage settings across different environments and evaluation scenarios.

## Configuration File Location

Default configuration locations (in order of precedence):

1. Path specified with `--config-file` option
2. `./vllm-eval.toml` (current directory)
3. `~/.config/vllm-eval/config.toml` (user config)
4. `/etc/vllm-eval/config.toml` (system config)

## Basic Configuration

### Example Configuration

```toml
# Global settings
profile_name = "default"
description = "Default VLLM evaluation configuration"
log_level = "INFO"

[model]
name = "my-model"
endpoint = "http://localhost:8000/v1/completions"
max_tokens = 2048
batch_size = 1

[system]
results_dir = "./results"
logs_dir = "./logs"
timeout_default = 3600

[evaluation]
# Framework configurations
[evaluation.evalchemy]
enabled = true
tasks = ["mmlu", "arc_easy", "hellaswag"]

[evaluation.nvidia_eval]
enabled = true
benchmark = "aime"
gpus = 1

[evaluation.vllm_benchmark]
enabled = true
scenario = "performance"
concurrency = 10

[evaluation.deepeval]
enabled = true
suite = "default"
metrics = ["precision", "recall"]
```

## Profile Management

### Creating Profiles

```bash
# Create new profile
vllm-eval config create production

# Create from existing profile
vllm-eval config create testing --from-profile default
```

### Using Profiles

```bash
# Use profile for single command
vllm-eval --profile production run evalchemy my-model

# Set default profile
vllm-eval config set-default production
```

## Framework Configuration

### Evalchemy

```toml
[evaluation.evalchemy]
enabled = true
endpoint = "http://localhost:8000/v1/completions"
batch_size = 4
timeout = 3600
tasks = ["mmlu", "arc_easy", "arc_challenge", "hellaswag"]
```

### NVIDIA Eval

```toml
[evaluation.nvidia_eval]
enabled = true
benchmark = "aime"  # or "livecodebench"
gpus = 2
out_seq_len = 4096
```

### VLLM Benchmark

```toml
[evaluation.vllm_benchmark]
enabled = true
scenario = "performance"
concurrency = 20
duration = 600
```

### Deepeval

```toml
[evaluation.deepeval]
enabled = true
suite = "rag"
metrics = ["faithfulness", "answer_relevancy"]
```

## Environment Variables

Configuration supports environment variable substitution:

```toml
[model]
endpoint = "${VLLM_ENDPOINT:-http://localhost:8000/v1}"
api_key = "${API_KEY}"

[system]
results_dir = "${RESULTS_DIR:-./results}"
```

## Validation

```bash
# Validate current configuration
vllm-eval config validate

# Test endpoint connectivity
vllm-eval config validate --test-endpoints
```

For more information, see:
- [Commands Reference](commands.md)
- [Troubleshooting](troubleshooting.md)
