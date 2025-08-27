# Commands Reference

Complete reference for all VLLM Evaluation CLI commands.

## Core Commands

### `vllm-eval run`

Execute evaluation frameworks with specified models and configurations.

#### Subcommands

##### `vllm-eval run evalchemy`

Run Evalchemy benchmark evaluation.

```bash
vllm-eval run evalchemy <model-name> [OPTIONS]
```

**Arguments:**
- `model-name`: Name or identifier of the model to evaluate

**Options:**
- `--endpoint TEXT`: VLLM server endpoint URL (default: http://localhost:8000/v1)
- `--batch-size INTEGER`: Number of requests to process in parallel (default: 1)
- `--config TEXT`: Configuration profile to use (default: default)
- `--dry-run`: Show what would be executed without running
- `--output-dir PATH`: Directory to save results (default: ./results)

**Examples:**
```bash
# Basic evaluation
vllm-eval run evalchemy my-model

# With custom endpoint and batch size
vllm-eval run evalchemy my-model --endpoint http://localhost:8000/v1 --batch-size 4

# Using production configuration
vllm-eval run evalchemy my-model --config production
```

##### `vllm-eval run nvidia`

Run NVIDIA evaluation suite (AIME, LiveCodeBench).

```bash
vllm-eval run nvidia <model-name> [OPTIONS]
```

**Options:**
- `--benchmark TEXT`: Benchmark to run (aime, livecodebench)
- `--gpus INTEGER`: Number of GPUs to use (default: 1)
- `--out-seq-len INTEGER`: Maximum output sequence length (default: 2048)

##### `vllm-eval run vllm-benchmark`

Run VLLM performance benchmarks.

```bash
vllm-eval run vllm-benchmark <model-name> [OPTIONS]
```

**Options:**
- `--scenario TEXT`: Benchmark scenario (performance, throughput, latency)
- `--concurrency INTEGER`: Number of concurrent requests (default: 10)
- `--duration INTEGER`: Test duration in seconds (default: 300)

##### `vllm-eval run deepeval`

Run Deepeval testing framework.

```bash
vllm-eval run deepeval <model-name> [OPTIONS]
```

**Options:**
- `--suite TEXT`: Test suite to run (default, rag, custom)
- `--metrics TEXT`: Comma-separated metrics (precision, recall, faithfulness)

##### `vllm-eval run all`

Run all enabled frameworks sequentially.

```bash
vllm-eval run all <model-name> [OPTIONS]
```

**Options:**
- `--frameworks TEXT`: Comma-separated list of frameworks to run
- `--continue-on-error`: Continue running other frameworks if one fails
- `--parallel`: Run frameworks in parallel (experimental)

## Configuration Commands

### `vllm-eval config`

Manage configuration profiles and settings.

#### Subcommands

##### `vllm-eval config show`

Display current configuration.

```bash
vllm-eval config show [OPTIONS]
```

**Options:**
- `--profile TEXT`: Show specific profile (default: current)
- `--format TEXT`: Output format (yaml, json, table)

##### `vllm-eval config create`

Create a new configuration profile.

```bash
vllm-eval config create <profile-name> [OPTIONS]
```

**Options:**
- `--from-profile TEXT`: Copy settings from existing profile
- `--interactive`: Use interactive setup wizard

##### `vllm-eval config validate`

Validate configuration syntax and connectivity.

```bash
vllm-eval config validate [OPTIONS]
```

**Options:**
- `--profile TEXT`: Validate specific profile
- `--test-endpoints`: Test endpoint connectivity

## System Commands

### `vllm-eval doctor`

Comprehensive system diagnostics and health checks.

```bash
vllm-eval doctor [OPTIONS]
```

**Options:**
- `--verbose`: Show detailed diagnostic information
- `--fix`: Attempt to fix common issues automatically

### `vllm-eval setup`

Interactive setup wizard for initial configuration.

```bash
vllm-eval setup [OPTIONS]
```

**Options:**
- `--no-interactive`: Use default values without prompts
- `--force`: Overwrite existing configuration

## Results Commands

### `vllm-eval results`

Manage and analyze evaluation results.

#### Subcommands

##### `vllm-eval results list`

List available evaluation results.

```bash
vllm-eval results list [OPTIONS]
```

##### `vllm-eval results show`

Display detailed results for a specific run.

```bash
vllm-eval results show <run-id> [OPTIONS]
```

##### `vllm-eval results export`

Export results in various formats.

```bash
vllm-eval results export <run-id> [OPTIONS]
```

**Options:**
- `--format TEXT`: Export format (json, csv, xlsx)
- `--output PATH`: Output file path

## Global Options

All commands support these global options:

- `--help`: Show help message and exit
- `--version`: Show version information
- `--verbose`: Enable verbose output
- `--quiet`: Suppress non-error output
- `--config-file PATH`: Use specific configuration file

## Examples

### Common Workflows

```bash
# Initial setup
vllm-eval setup

# Quick evaluation with defaults
vllm-eval run evalchemy my-model

# Production evaluation with full configuration
vllm-eval run all my-model --config production --output-dir ./prod-results

# Troubleshooting
vllm-eval doctor --verbose
vllm-eval config validate --test-endpoints
```

For more detailed information, see:
- [Configuration Guide](configuration.md)
- [Troubleshooting](troubleshooting.md)
