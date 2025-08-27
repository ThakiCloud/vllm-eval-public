# VLLM Evaluation CLI - Updated Usage Guide

This document describes the updated VLLM Evaluation CLI with all the recent improvements and new features.

## 🚀 What's New

### ✨ New Commands
- **`vllm-eval run quick`** - Quick evaluation with minimal configuration
- **`vllm-eval system validate`** - Comprehensive configuration validation
- **Enhanced `vllm-eval run all`** - Framework selection and improved error handling
- **Improved `vllm-eval setup`** - Better validation and non-interactive mode

### 🛠️ Improvements
- **Fixed import warnings** and improved entry point configuration
- **Enhanced help text** with rich formatting and examples
- **Better error handling** with continue-on-error options
- **Configuration validation** with endpoint connectivity testing
- **Improved command consistency** across all frameworks

## 📚 Complete Command Reference

### Main CLI
```bash
# Show enhanced help with examples
vllm-eval --help

# Show version information
vllm-eval version

# Run system diagnostics
vllm-eval doctor
```

### Setup and Configuration
```bash
# Interactive setup wizard with validation
vllm-eval setup

# Non-interactive setup with defaults
vllm-eval setup --no-interactive

# Force overwrite existing configuration
vllm-eval setup --force

# Validate configuration and connectivity
vllm-eval system validate

# Validate specific config file
vllm-eval system validate --config ./my-config.toml
```

### Quick Evaluation (NEW!)
```bash
# Quick evaluation with default framework (evalchemy)
vllm-eval run quick my-model --endpoint http://localhost:8000

# Quick evaluation with specific framework
vllm-eval run quick my-model --framework deepeval

# Quick evaluation with custom output
vllm-eval run quick my-model \
  --framework nvidia \
  --endpoint http://localhost:8000 \
  --output ./results/quick-test

# Dry run to see what would be executed
vllm-eval run quick my-model --dry-run
```

### Framework-Specific Evaluations
```bash
# Evalchemy with enhanced options
vllm-eval run evalchemy my-model \
  --endpoint http://localhost:8000/v1/completions \
  --batch-size 16 \
  --config-name custom_config \
  --run-id "experiment_001"

# Standard Evalchemy evaluation
vllm-eval run standard-evalchemy my-model \
  --endpoint http://localhost:8000/v1/completions \
  --batch-size 8

# NVIDIA evaluation with flexible options
vllm-eval run nvidia my-model \
  --benchmark aime \
  --model-path /path/to/model \
  --gpus 4 \
  --out-seq-len 4096

# VLLM Benchmark with performance scenarios
vllm-eval run vllm-benchmark my-model \
  --scenario throughput \
  --endpoint http://localhost:8000 \
  --concurrency 64 \
  --duration 300

# Deepeval with custom metrics
vllm-eval run deepeval my-model \
  --suite rag_tests \
  --metrics "answer_relevancy,contextual_relevancy" \
  --endpoint http://localhost:8000/v1
```

### Enhanced All-Framework Evaluation
```bash
# Run all enabled frameworks (from config)
vllm-eval run all my-model

# Run specific frameworks
vllm-eval run all my-model \
  --frameworks evalchemy,deepeval,nvidia \
  --endpoint http://localhost:8000

# Run with enhanced error handling
vllm-eval run all my-model \
  --frameworks evalchemy,vllm-benchmark \
  --continue-on-error \
  --verbose

# Stop on first error
vllm-eval run all my-model \
  --frameworks evalchemy,deepeval \
  --stop-on-error

# Parallel execution (when implemented)
vllm-eval run all my-model --parallel
```

### System Management
```bash
# System status and health
vllm-eval system status
vllm-eval system status --verbose

# Comprehensive diagnostics
vllm-eval system doctor
vllm-eval system doctor --fix

# System cleanup
vllm-eval system clean
vllm-eval system clean --no-cache --logs

# Configuration validation (NEW!)
vllm-eval system validate
vllm-eval system validate --verbose
vllm-eval system validate --config ./custom-config.toml
```

### Configuration Management
```bash
# Show current configuration
vllm-eval config show

# List available profiles
vllm-eval config list

# Use specific profile
vllm-eval --profile production run quick my-model
```

### Results Management
```bash
# List recent results
vllm-eval results list

# Show specific result
vllm-eval results show <result_id>

# Export results
vllm-eval results export <result_id> --format json
```

## 🔧 Configuration Examples

### Basic Configuration
```toml
# ~/.config/vllm-eval/default.toml
default_endpoint = "http://localhost:8000/v1"
default_model = "my-default-model"

[system]
results_dir = "./results"
default_batch_size = 8
default_timeout = 3600
log_level = "INFO"

[frameworks.evalchemy]
enabled = true
config_name = "standard"

[frameworks.deepeval]
enabled = true
test_suite = "default"

[frameworks.nvidia]
enabled = false

[frameworks.vllm_benchmark]
enabled = true
scenario = "performance"
```

### Advanced Configuration
```toml
# Production profile configuration
default_endpoint = "https://api.company.com/v1"
default_model = "company/production-model"

[system]
results_dir = "/opt/vllm-eval/results"
default_batch_size = 16
default_timeout = 7200
log_level = "WARNING"

[frameworks.evalchemy]
enabled = true
config_name = "production"
batch_size = 32
timeout = 3600

[frameworks.deepeval]
enabled = true
test_suite = "production_rag"
metrics = ["answer_relevancy", "contextual_relevancy", "faithfulness"]

[frameworks.nvidia]
enabled = true
benchmark = "aime"
gpus = 8
out_seq_len = 8192

[frameworks.vllm_benchmark]
enabled = true
scenario = "high_throughput"
concurrency = 128
duration = 1800
```

## 🎯 Best Practices

### 1. Setup Workflow
```bash
# 1. Run setup wizard
vllm-eval setup

# 2. Validate configuration
vllm-eval system validate

# 3. Test with quick evaluation
vllm-eval run quick test-model --dry-run

# 4. Run diagnostics if issues
vllm-eval doctor
```

### 2. Production Usage
```bash
# Use profiles for different environments
vllm-eval --profile production run all my-model

# Always validate before important runs
vllm-eval system validate --config ./production.toml

# Use continue-on-error for comprehensive evaluation
vllm-eval run all my-model --continue-on-error --verbose
```

### 3. Development and Testing
```bash
# Use dry-run for testing commands
vllm-eval run all my-model --dry-run

# Quick iterations with specific frameworks
vllm-eval run quick my-model --framework evalchemy

# Clean up between runs
vllm-eval system clean
```

## 🐛 Troubleshooting

### Configuration Issues
```bash
# Validate configuration
vllm-eval system validate --verbose

# Check system status
vllm-eval system status --verbose

# Run full diagnostics
vllm-eval doctor --fix
```

### Endpoint Connectivity
```bash
# Test endpoint in validation
vllm-eval system validate

# Use verbose mode for detailed errors
vllm-eval run quick my-model --verbose

# Check with dry-run first
vllm-eval run quick my-model --dry-run
```

### Framework-Specific Issues
```bash
# Test individual frameworks
vllm-eval run quick my-model --framework evalchemy --dry-run

# Check framework configuration
vllm-eval config show

# Use verbose output for debugging
vllm-eval run evalchemy my-model --verbose
```

## 📈 Performance Tips

1. **Use appropriate batch sizes** for your hardware
2. **Leverage the quick command** for rapid testing
3. **Use framework selection** to run only needed evaluations
4. **Enable parallel execution** when available
5. **Monitor system resources** during long evaluations

## 🔗 Integration Examples

### CI/CD Integration
```bash
# Validate configuration in CI
vllm-eval system validate || exit 1

# Run core evaluations
vllm-eval run all my-model \
  --frameworks evalchemy,deepeval \
  --output ./ci-results \
  --continue-on-error

# Check results and exit appropriately
vllm-eval results list --latest
```

### Automated Testing
```bash
# Quick smoke test
vllm-eval run quick $MODEL_NAME --dry-run

# Comprehensive evaluation
vllm-eval run all $MODEL_NAME \
  --endpoint $ENDPOINT \
  --output ./automated-results \
  --verbose
```

This updated CLI provides a much more robust, user-friendly, and feature-rich experience for VLLM model evaluation!