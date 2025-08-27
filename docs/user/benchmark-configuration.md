# Benchmark Configuration# Benchmark Configuration

Comprehensive guide to configuring benchmarks and evaluation parameters using the VLLM Evaluation CLI. Learn how to customize evaluations for different frameworks, manage configuration profiles, and optimize settings for your specific use cases.

!!! info "Configuration Management"
    
    - ⚙️ **Profile-Based**: Environment-specific configurations
    - 📋 **TOML Format**: Human-readable configuration files
    - ✅ **Validation**: Built-in configuration and connectivity testing
    - 🔄 **Inheritance**: Profile inheritance and override capabilities

## Configuration Overview

### Configuration Hierarchy

The CLI uses a hierarchical configuration system with multiple sources:

1. **Command-line arguments** (highest priority)
2. **Profile-specific TOML files**
3. **Default configuration**
4. **Environment variables**

```bash
# Configuration precedence example
vllm-eval --config ./custom.toml \
          --profile production \
          run evalchemy my-model \
          --batch-size 4         # CLI args override config
```

---

## ⚙️ Profile Management

### Creating and Managing Profiles

```bash
# Create new profile
vllm-eval config create development
vllm-eval config create production
vllm-eval config create ci-cd

# List available profiles
vllm-eval config list-profiles

# Show profile configuration
vllm-eval config show --profile production

# Set default profile
vllm-eval config set-default production

# Copy profile with modifications
vllm-eval config create staging --from-profile production
```

### Profile Structure

Configuration files are stored in `~/.config/vllm-eval/`:

```
~/.config/vllm-eval/
├── config.toml              # Default configuration
├── development.toml         # Development profile  
├── production.toml          # Production profile
├── ci-cd.toml              # CI/CD profile
└── logs/                   # Configuration logs
```

---

## 📋 Framework Configuration

### Evalchemy Configuration

#### Basic Configuration

```toml
[evaluation.evalchemy]
enabled = true
endpoint = "http://localhost:8000/v1/completions"
batch_size = 4
timeout = 3600

# Task selection
tasks = [
    "mmlu",           # Massive Multitask Language Understanding  
    "arc_easy",       # AI2 Reasoning Challenge (Easy)
    "arc_challenge",  # AI2 Reasoning Challenge (Hard)
    "hellaswag",      # Common sense reasoning
    "humaneval",      # Code generation
]

# Advanced configuration
num_fewshot = 0
limit = null              # No limit on test cases
include_path = "./custom-tasks/"
```

#### Task-Specific Settings

```toml
[evaluation.evalchemy.tasks]
# MMLU configuration
mmlu = {
    enabled = true,
    num_fewshot = 5,
    limit = 1000,
    categories = ["humanities", "social_sciences", "stem"]
}

# HumanEval configuration  
humaneval = {
    enabled = true,
    num_fewshot = 0,
    temperature = 0.0,
    max_tokens = 512
}

# Custom task configuration
custom_reasoning = {
    enabled = true,
    task_file = "./custom-tasks/reasoning.json",
    metric = "exact_match"
}
```

#### Generation Parameters

```toml
[evaluation.evalchemy.generation]
temperature = 0.0
top_p = 1.0
max_tokens = 2048
stop_sequences = ["\n\n", "###"]

# Model-specific overrides
[evaluation.evalchemy.model_overrides]
"gpt-4" = { temperature = 0.1, max_tokens = 4096 }
"claude-3" = { temperature = 0.0, top_p = 0.95 }
```

### NVIDIA Eval Configuration

#### AIME Benchmark

```toml
[evaluation.nvidia_eval]
enabled = true
benchmark = "aime"         # or "livecodebench"
model_path = "/path/to/model"  # Optional, auto-detect if not specified
gpus = 2
out_seq_len = 4096
timeout = 7200

# AIME-specific settings
[evaluation.nvidia_eval.aime]
num_problems = 30          # Number of problems to evaluate
temperature = 0.0
top_p = 1.0 
max_new_tokens = 2048
use_sampling = false       # Deterministic generation

# Problem selection
problem_years = [2023, 2024]  # Specific years
difficulty_range = [1, 15]     # Problem difficulty (1-15)
```

#### LiveCodeBench Configuration

```toml
[evaluation.nvidia_eval.livecodebench]
contest_range = "2024-01-01:2024-12-31"
languages = ["python", "java", "cpp"]
max_context_length = 8192
generate_tests = true

# Language-specific settings
[evaluation.nvidia_eval.livecodebench.python]
runner = "python3.11"
timeout = 30              # seconds per test
memory_limit = "512MB"

[evaluation.nvidia_eval.livecodebench.java]
runner = "openjdk-17"
timeout = 45
memory_limit = "1GB"
```

### VLLM Benchmark Configuration

#### Performance Testing

```toml
[evaluation.vllm_benchmark]
enabled = true
endpoint = "http://localhost:8000"
scenario = "performance"   # performance, throughput, latency

# Load testing parameters
concurrency = 20
duration = 600            # seconds
warmup_time = 60         # seconds
request_rate = 10        # requests per second (0 = max rate)

# Request configuration
input_length = 1024
output_length = 128
max_tokens = 2048
```

#### Scenario-Specific Settings

```toml
[evaluation.vllm_benchmark.scenarios]
# Performance scenario: balanced load testing
performance = {
    concurrency = 20,
    duration = 600,
    request_rate = 10,
    metrics = ["ttft", "tpot", "throughput", "latency"]
}

# Throughput scenario: maximum throughput testing
throughput = {
    concurrency = 50,
    duration = 300,
    request_rate = 0,      # Maximum rate
    input_lengths = [512, 1024, 2048],
    output_lengths = [64, 128, 256]
}

# Latency scenario: low-latency testing
latency = {
    concurrency = 1,
    duration = 180,
    request_rate = 1,
    input_length = 512,
    output_length = 32,
    percentiles = [50, 90, 95, 99]
}
```

### Deepeval Configuration

#### RAG Evaluation

```toml
[evaluation.deepeval]
enabled = true
endpoint = "http://localhost:8000/v1/completions"
suite = "rag"             # default, rag, custom

# Metrics selection
metrics = [
    "faithfulness",        # RAG faithfulness
    "answer_relevancy",    # Answer relevance
    "context_precision",   # Context precision
    "context_recall"       # Context recall
]

# Test data configuration
test_cases_file = "./test_cases.json"
context_file = "./knowledge_base.json"
max_test_cases = 100
```

#### Custom Metrics Configuration

```toml
[evaluation.deepeval.custom_metrics]
# Custom faithfulness threshold
faithfulness = {
    threshold = 0.7,
    model = "gpt-4",
    include_reason = true
}

# Custom relevancy metric
relevancy = {
    threshold = 0.8,
    strict_mode = true,
    async_mode = false
}

# Custom G-Eval metric
custom_correctness = {
    name = "Correctness",
    criteria = "Determine whether the actual output is factually correct based on the expected output.",
    evaluation_steps = [
        "Check if the main facts in the actual output align with the expected output",
        "Verify that there are no factual errors or contradictions",
        "Assess the completeness of the information provided"
    ],
    evaluation_params = ["factual_accuracy", "completeness", "consistency"]
}
```

---

## 🏢 Environment-Specific Configurations

### Development Profile

```toml
# ~/.config/vllm-eval/development.toml
profile_name = "development"
description = "Development environment settings"
log_level = "DEBUG"
dry_run = false

[model]
name = "test-model"
endpoint = "http://localhost:8000/v1/completions"
batch_size = 1

[system]
results_dir = "./dev-results"
timeout_default = 1800    # Shorter timeouts for dev
max_concurrent_jobs = 1

[evaluation.evalchemy]
enabled = true
tasks = ["arc_easy"]      # Subset for faster iteration
batch_size = 1
timeout = 1800
limit = 50               # Limit test cases for speed

[evaluation.deepeval]
enabled = true
metrics = ["faithfulness"] # Single metric for quick tests
max_test_cases = 10

[evaluation.nvidia_eval]
enabled = false           # Skip GPU-intensive tests in dev

[evaluation.vllm_benchmark]
enabled = true
scenario = "latency"
concurrency = 1
duration = 60            # Short performance test
```

### Production Profile

```toml
# ~/.config/vllm-eval/production.toml
profile_name = "production"
description = "Production evaluation settings"
log_level = "INFO"
dry_run = false

[model]
name = "${MODEL_NAME}"    # Environment variable
endpoint = "${VLLM_ENDPOINT:-https://api.production.com/v1/completions}"
batch_size = 8

[system]
results_dir = "${RESULTS_DIR:-/shared/results}"
timeout_default = 7200
max_concurrent_jobs = 4
log_retention_days = 90

[evaluation.evalchemy]
enabled = true
tasks = ["mmlu", "arc_easy", "arc_challenge", "hellaswag", "humaneval"]
batch_size = 8
timeout = 7200

[evaluation.nvidia_eval]
enabled = true
benchmark = "aime"
gpus = 4
timeout = 10800

[evaluation.vllm_benchmark]
enabled = true
scenario = "performance"
concurrency = 50
duration = 1800

[evaluation.deepeval]
enabled = true
metrics = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]
max_test_cases = 1000

[output]
format = "json"
compress_results = true
include_raw_responses = false  # Save storage in production
```

### CI/CD Profile

```toml
# ~/.config/vllm-eval/ci-cd.toml
profile_name = "ci-cd"
description = "Continuous integration settings"
log_level = "INFO"
dry_run = false

[model]
name = "${CI_MODEL_NAME}"
endpoint = "${CI_VLLM_ENDPOINT}"
batch_size = 2

[system]
results_dir = "${CI_RESULTS_DIR:-./ci-results}"
timeout_default = 3600    # Limit CI time
max_concurrent_jobs = 2

[evaluation.evalchemy]
enabled = true
tasks = ["arc_easy", "mmlu"]  # Essential tasks only
batch_size = 2
timeout = 3600
limit = 200              # Limit for CI speed

[evaluation.nvidia_eval]
enabled = false          # Skip in CI for time

[evaluation.vllm_benchmark]
enabled = true
scenario = "latency"
concurrency = 5
duration = 300

[evaluation.deepeval]
enabled = false          # Skip in CI for speed

[output]
format = "json"
compress_results = true
export_to_artifact = true
```

---

## 📊 Advanced Configuration Patterns

### Variable Substitution

```toml
# Environment variables with defaults
[model]
endpoint = "${VLLM_ENDPOINT:-http://localhost:8000/v1}"
api_key = "${API_KEY}"    # Required environment variable
model_name = "${MODEL_NAME:-default-model}"

# Cross-reference within config
[evaluation.evalchemy]
endpoint = "${model.endpoint}"
batch_size = "${model.batch_size:-1}"

# Computed values
[system]
results_dir = "${HOME}/.vllm-eval/results/${model.name}"
log_file = "${system.results_dir}/evaluation.log"
```

### Conditional Configuration

```toml
# GPU availability detection
[evaluation.nvidia_eval]
enabled = "${HAS_GPU:-false}"  # Enable only if GPU available
gpus = "${GPU_COUNT:-1}"

# Environment-based settings
[evaluation.evalchemy]
tasks = "${EVALCHEMY_TASKS:-[mmlu,arc_easy]}"
limit = "${CI:-false}" == "true" ? 100 : null  # Limit in CI
```

### Profile Inheritance

```toml
# staging.toml inherits from production.toml
[inherit]
from = "production"

# Override specific settings
[evaluation.evalchemy]
limit = 500              # Reduced test set for staging

[evaluation.vllm_benchmark]
duration = 900           # Shorter performance test
```

---

## ✅ Configuration Validation

### Built-in Validation

```bash
# Validate configuration syntax and completeness
vllm-eval config validate

# Test endpoint connectivity
vllm-eval config validate --test-endpoints

# Validate specific profile
vllm-eval config validate --profile production

# Check configuration resolution (with variables)
vllm-eval config show --expand-variables
```

### Custom Validation Rules

```toml
[validation]
# Endpoint requirements
require_https_in_production = true
allow_localhost_in_dev = true

# Resource limits
max_batch_size = 32
max_concurrent_jobs = 10
max_timeout = 14400      # 4 hours

# Framework requirements
require_at_least_one_framework = true
warn_on_gpu_requirements = true
```

### Validation Output

```bash
vllm-eval config validate
```

```
✅ Configuration Validation Results

📋 Profile: production
✅ Syntax: Valid TOML format
✅ Schema: All required fields present
✅ Variables: All environment variables resolved
⚠️  Endpoints: 
  ✅ evalchemy: http://api.prod.com/v1 (200 OK)
  ❌ deepeval: http://api.prod.com/v1 (Connection timeout)
✅ Resources: Within limits
✅ Frameworks: 3/4 enabled and validated

🚨 Issues Found:
  ❌ deepeval endpoint unreachable
  ⚠️  nvidia_eval requires GPU but none detected

💡 Suggestions:
  - Check deepeval endpoint configuration
  - Set nvidia_eval.enabled = false for CPU-only environments
  - Consider increasing timeout for large models
```

---

## 🔄 Configuration Workflows

### Development to Production

```bash
# 1. Develop and test locally
vllm-eval --profile development run evalchemy my-model --dry-run
vllm-eval --profile development run evalchemy my-model --limit 10

# 2. Create staging configuration
vllm-eval config create staging --from-profile development
vllm-eval config edit staging  # Adjust for staging environment

# 3. Test staging configuration
vllm-eval --profile staging config validate --test-endpoints
vllm-eval --profile staging run all my-model --dry-run

# 4. Deploy to production
vllm-eval config create production --from-profile staging
vllm-eval --profile production config validate
```

### Team Configuration Sharing

```bash
# Export configuration for sharing
vllm-eval config export --profile production > team-config.toml

# Import team configuration
vllm-eval config import team-config.toml --profile team-shared

# Version control integration
cp ~/.config/vllm-eval/production.toml ./configs/
git add configs/production.toml
git commit -m "Add production evaluation configuration"
```

### Automated Configuration Management

```bash
# Generate configuration from template
envsubst < config-template.toml > ~/.config/vllm-eval/auto-generated.toml

# Validate in CI/CD
vllm-eval config validate --profile ci-cd --exit-on-error

# Deploy configuration
kubectl create configmap vllm-eval-config --from-file=production.toml
```

---

## 🛠️ Configuration Troubleshooting

### Common Issues

#### 1. Configuration Not Found

```bash
# Error: Configuration file not found
# Solution: Run setup wizard
vllm-eval setup --force

# Or create minimal configuration
mkdir -p ~/.config/vllm-eval
echo 'profile_name = "default"' > ~/.config/vllm-eval/config.toml
```

#### 2. Invalid TOML Syntax

```bash
# Error: TOML parsing failed
# Check syntax
vllm-eval config validate --check-syntax

# Common issues:
# - Missing quotes around strings
# - Invalid escape sequences
# - Mismatched brackets
```

#### 3. Environment Variable Resolution

```bash
# Error: Environment variable not found
# Check variable expansion
vllm-eval config show --expand-variables

# Set missing variables
export VLLM_ENDPOINT="http://localhost:8000/v1"
export MODEL_NAME="my-model"
```

#### 4. Endpoint Connectivity

```bash
# Error: Connection refused
# Test endpoints
vllm-eval config validate --test-endpoints --verbose

# Manual testing
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "test", "prompt": "Hello", "max_tokens": 5}'
```

### Debug Mode

```bash
# Enable debug logging for configuration
export VLLM_EVAL_DEBUG_CONFIG=1
vllm-eval --debug config show

# Trace configuration loading
vllm-eval --debug --verbose config validate
```

---

## 🔗 Related Documentation

### Configuration References
- **[CLI Configuration Guide](../cli/configuration.md)** - Detailed CLI configuration documentation
- **[CLI Commands Reference](../cli/commands.md)** - Command-line usage patterns
- **[CLI Troubleshooting](../cli/troubleshooting.md)** - Configuration problem resolution

### Framework Documentation
- **[Evalchemy API](../api/evalchemy-api.md)** - Evalchemy configuration details
- **[NVIDIA Eval API](../api/nvidia-eval-api.md)** - NVIDIA evaluation setup
- **[VLLM Benchmark API](../api/vllm-benchmark-api.md)** - Performance testing configuration
- **[Deepeval API](../api/deepeval-api.md)** - Custom metrics configuration

### Advanced Topics
- **[Result Interpretation](result-interpretation.md)** - Understanding evaluation results
- **[Architecture Overview](../architecture/system-overview.md)** - System architecture
- **[Operations Guide](../operations/monitoring-guide.md)** - Production configuration management

!!! success "Configuration Mastery"
    
    You now have comprehensive knowledge of benchmark configuration management.
    
    **Quick Start**: `vllm-eval config create my-profile && vllm-eval config edit my-profile`
    
    **Next**: Explore [Result Interpretation](result-interpretation.md) to understand your evaluation results.
