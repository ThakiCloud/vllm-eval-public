# CLI Overview

The VLLM Evaluation CLI (`vllm-eval`) is a unified command-line interface for running model evaluations across multiple frameworks. It provides a streamlined way to execute benchmarks, manage configurations, and analyze results without dealing with framework-specific setup complexities.

!!! info "Key Features"
    
    - 🚀 **Unified Interface**: Single CLI for all evaluation frameworks
    - 🔧 **Configuration Management**: TOML-based profiles and settings
    - 📊 **Rich Output**: Beautiful terminal displays with progress indicators
    - 🧪 **Multiple Frameworks**: Support for Evalchemy, NVIDIA Eval, VLLM Benchmark, and Deepeval
    - 🔍 **System Diagnostics**: Built-in health checks and troubleshooting
    - 📋 **Results Management**: Standardized result formats and comparison tools

## Supported Evaluation Frameworks

The CLI integrates with multiple evaluation frameworks through a unified adapter pattern:

### Evalchemy
- **Purpose**: Comprehensive benchmark suite (MMLU, HumanEval, ARC, HellaSwag)
- **Specialization**: Academic benchmarks and standard evaluations
- **Output**: Detailed accuracy metrics and performance analysis

### NVIDIA Eval
- **Purpose**: Mathematical reasoning and coding benchmarks
- **Specialization**: AIME 2024 and LiveCodeBench evaluations
- **Output**: Problem-solving accuracy and reasoning capabilities

### VLLM Benchmark
- **Purpose**: Performance and throughput testing
- **Specialization**: TTFT (Time to First Token), TPOT (Time Per Output Token), throughput
- **Output**: Performance metrics and latency analysis

### Deepeval
- **Purpose**: Custom metrics and RAG evaluation
- **Specialization**: Context relevance, faithfulness, answer relevancy
- **Output**: Quality assessment for retrieval-augmented generation

## Quick Start

### Installation

```bash
# Install from project directory
cd /path/to/vllm-eval-public
pip install -e .
```

### Setup

```bash
# Run interactive setup wizard
vllm-eval setup

# Check installation and system status
vllm-eval doctor

# View available commands
vllm-eval --help
```

### Basic Usage

```bash
# Run Evalchemy evaluation
vllm-eval run evalchemy my-model --endpoint http://localhost:8000/v1

# Run all enabled frameworks
vllm-eval run all my-model

# Run with custom configuration profile
vllm-eval run evalchemy my-model --config production --batch-size 4

# Dry run to preview execution
vllm-eval run evalchemy my-model --dry-run
```

## Next Steps

- [Commands Reference](commands.md) - Detailed command documentation
- [Configuration Guide](configuration.md) - Setup and profile management  
- [Troubleshooting](troubleshooting.md) - Common issues and solutions
- [API Documentation](../api/evalchemy-api.md) - Framework-specific details