# VLLM Evaluation CLI

A comprehensive command-line interface for running VLLM model evaluations across multiple frameworks.

## Features

- 🚀 **Unified Interface**: Single CLI for all evaluation frameworks
- 🔧 **Configuration Management**: TOML-based profiles and settings
- 📊 **Rich Output**: Beautiful terminal displays with progress indicators
- 🧪 **Multiple Frameworks**: Support for Evalchemy, NVIDIA Eval, VLLM Benchmark, and Deepeval
- 🔍 **System Diagnostics**: Built-in health checks and troubleshooting
- 📋 **Results Management**: Standardized result formats and comparison tools

## Quick Start

### Installation

```bash
# Install in development mode
pip install -e .

# Or install from the project directory
cd /Users/yakhyo/Projects/vllm-eval-public
pip install -e .
```

### Setup

```bash
# Run the setup wizard
vllm-eval setup

# Check system status
vllm-eval system status

# View help
vllm-eval --help
```

### Basic Usage

```bash
# Run Evalchemy evaluation
vllm-eval run evalchemy my-model --endpoint http://localhost:8000/v1

# Run all enabled frameworks
vllm-eval run all my-model

# Run with custom configuration
vllm-eval run evalchemy my-model --config production --batch-size 4

# Dry run to see what would be executed
vllm-eval run evalchemy my-model --dry-run
```

## Available Commands

### Run Commands
- `vllm-eval run evalchemy` - Run Evalchemy benchmark evaluation
- `vllm-eval run standard-evalchemy` - Run Standard Evalchemy evaluation
- `vllm-eval run nvidia` - Run NVIDIA evaluation suite (AIME, LiveCodeBench)
- `vllm-eval run vllm-benchmark` - Run VLLM performance benchmarks
- `vllm-eval run deepeval` - Run Deepeval testing framework
- `vllm-eval run all` - Run all enabled frameworks

### Configuration Commands
- `vllm-eval config show` - Show current configuration
- `vllm-eval config list-profiles` - List available profiles
- `vllm-eval config create <name>` - Create new profile
- `vllm-eval config edit` - Edit configuration interactively
- `vllm-eval config validate` - Validate configuration

### System Commands
- `vllm-eval system status` - Show system status
- `vllm-eval system doctor` - Diagnose and fix issues
- `vllm-eval system clean` - Clean up temporary files
- `vllm-eval system logs` - View system logs

### Results Commands
- `vllm-eval results list` - List evaluation results
- `vllm-eval results show <run-id>` - Show detailed results
- `vllm-eval results export <run-id>` - Export results

## Framework-Specific Options

### Evalchemy
```bash
vllm-eval run evalchemy my-model \
  --endpoint http://localhost:8000/v1 \
  --batch-size 4 \
  --config production \
  --run-id custom-run-001
```

### NVIDIA Eval
```bash
vllm-eval run nvidia my-model \
  --benchmark livecodebench \
  --model-path /path/to/model \
  --gpus 2 \
  --out-seq-len 2048
```

### VLLM Benchmark
```bash
vllm-eval run vllm-benchmark my-model \
  --scenario performance \
  --concurrency 10 \
  --duration 300 \
  --endpoint http://localhost:8000/v1
```

### Deepeval
```bash
vllm-eval run deepeval my-model \
  --suite rag \
  --metrics precision,recall,f1 \
  --endpoint http://localhost:8000/v1
```

## Configuration

Configuration is stored in TOML files located at `~/.config/vllm-eval/`. Each profile has its own configuration file.

### Example Configuration

```toml
# Global settings
default_model = "my-model"
default_endpoint = "http://localhost:8000/v1"
parallel_execution = false

[system]
results_dir = "./results"
logs_dir = "./logs"
cache_dir = "./cache"
log_level = "INFO"

[evalchemy]
enabled = true
endpoint = "http://localhost:8000/v1"
batch_size = 1
timeout = 3600
config_name = "default"

[nvidia_eval]
enabled = true
benchmark = "livecodebench"
gpu_count = 1
out_seq_len = 2048

[vllm_benchmark]
enabled = true
scenario = "performance"
concurrency = 10
duration = 300

[deepeval]
enabled = true
test_suite = "default"
metrics = ["precision", "recall"]
```

## Architecture

The CLI uses an adapter pattern to provide a unified interface to different evaluation frameworks:

```
CLI Interface
├── Commands (run, config, system, results)
├── Adapters (evalchemy, nvidia, vllm_benchmark, deepeval)
├── Core (configuration, results management)
└── UI (rich terminal output, progress indicators)
```

## Development

### Project Structure

```
vllm_eval_cli/
├── __init__.py
├── main.py                 # CLI entry point
├── core/
│   ├── config.py          # Configuration management
│   └── ...
├── commands/
│   ├── run.py             # Run command implementation
│   ├── config.py          # Config command implementation
│   └── ...
├── adapters/
│   ├── base.py            # Base adapter interface
│   ├── evalchemy.py       # Evalchemy adapter
│   └── ...
├── ui/
│   ├── console.py         # Rich console utilities
│   └── ...
└── utils/
    └── ...
```

### Adding New Frameworks

1. Create a new adapter class inheriting from `BaseEvaluationAdapter`
2. Implement required methods: `validate_prerequisites`, `prepare_execution`, `execute_evaluation`, `parse_results`
3. Register the adapter in `adapters/__init__.py`
4. Add configuration schema to `core/config.py`
5. Add command to `commands/run.py`

## Troubleshooting

### Common Issues

1. **Configuration not found**: Run `vllm-eval setup` to create initial configuration
2. **Framework validation errors**: Run `vllm-eval system doctor` to diagnose issues
3. **Permission errors**: Check file permissions with `vllm-eval system status`
4. **Docker issues**: Ensure Docker is installed and running

### Getting Help

```bash
# General help
vllm-eval --help

# Command-specific help
vllm-eval run --help
vllm-eval run evalchemy --help

# System diagnostics
vllm-eval system doctor

# Check logs
vllm-eval system logs
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes following the existing patterns
4. Test with `vllm-eval system doctor`
5. Submit a pull request

## License

Apache 2.0 License - see LICENSE file for details.