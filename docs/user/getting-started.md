# Getting Started

Welcome to the VLLM Evaluation System! This guide will help you get started with evaluating your language models using our unified CLI interface and comprehensive evaluation frameworks.

!!! info "Quick Overview"
    
    The VLLM Evaluation System provides:
    
    - 🚀 **Unified CLI**: Single interface for all evaluation frameworks
    - 🧪 **Multiple Frameworks**: Evalchemy, NVIDIA Eval, VLLM Benchmark, Deepeval
    - ⚙️ **Flexible Deployment**: Local CLI or Kubernetes production setup
    - 📊 **Rich Results**: Standardized metrics and comparison tools

## Choose Your Setup Path

### Option 1: CLI-Only Setup (Recommended for Getting Started)

Perfect for:
- Local development and testing
- Quick model evaluations
- Learning the system
- Rapid iteration

### Option 2: Full Kubernetes Setup

Perfect for:
- Production deployments
- Continuous evaluation pipelines
- Scalable processing
- Team collaboration

---

## 🚀 CLI-Only Setup (5 Minutes)

### Prerequisites

- **Python 3.11+**
- **Docker** (for model serving)
- **Git**

### Installation

```bash
# Clone the repository
git clone https://github.com/thakicloud/vllm-eval-public.git
cd vllm-eval-public

# Install CLI in development mode
pip install -e .

# Verify installation
vllm-eval --help
```

### Initial Setup

```bash
# Run interactive setup wizard
vllm-eval setup

# Check system status
vllm-eval doctor

# Validate configuration
vllm-eval config validate
```

The setup wizard will guide you through:
- Configuration profile creation
- Framework selection and setup
- Endpoint configuration
- Dependency installation

### Your First Evaluation

#### Step 1: Start a Model Server

```bash
# Option A: Use VLLM (recommended)
vllm serve microsoft/DialoGPT-medium --port 8000

# Option B: Use any OpenAI-compatible server
# Your server should expose /v1/completions endpoint
```

#### Step 2: Run Evaluation

```bash
# Quick evaluation with Evalchemy
vllm-eval run evalchemy my-model --endpoint http://localhost:8000/v1

# Or dry-run to see what would happen
vllm-eval run evalchemy my-model --dry-run
```

#### Step 3: View Results

```bash
# List all results
vllm-eval results list

# Show detailed results for latest run
vllm-eval results show <run-id>
```

### Next Steps with CLI

```bash
# Try different frameworks
vllm-eval run nvidia my-model --benchmark aime
vllm-eval run vllm-benchmark my-model --scenario performance
vllm-eval run deepeval my-model --suite rag

# Run all enabled frameworks
vllm-eval run all my-model

# Create custom configuration profiles
vllm-eval config create production
vllm-eval config create testing
```

---

## 🏗️ Full Kubernetes Setup

### Prerequisites

- **Docker Desktop** or **OrbStack** (for macOS)
- **kubectl**
- **Helm 3+**
- **Make** (for build automation)

### Installation

```bash
# Clone repository
git clone https://github.com/thakicloud/vllm-eval-public.git
cd vllm-eval-public

# Setup development environment
make dev-setup

# Deploy local Kubernetes cluster with dependencies
make kind-deploy

# Install Helm charts (ClickHouse, Grafana, Argo Workflows)
make helm-install

# Build and push Docker images
make build-images
make push-images
```

### Verification

```bash
# Check cluster status
kubectl get pods -A

# Run tests
make run-tests

# Submit test workflow
make submit-workflow

# Watch workflow execution
make watch-workflow
```

### Monitoring and Visualization

- **Grafana**: Access dashboards for performance metrics
- **ClickHouse**: Query evaluation results database
- **Argo Workflows**: Monitor evaluation pipeline execution

---

## 🛠️ Development Workflow

### Local Development with CLI

```bash
# 1. Setup development environment
make dev-setup
pip install -e .

# 2. Start model server
vllm serve your-model --port 8000

# 3. Develop and test
vllm-eval run evalchemy your-model --dry-run
vllm-eval run evalchemy your-model --batch-size 2

# 4. View and analyze results
vllm-eval results list
vllm-eval results show <run-id> --format json
```

### Production Deployment

```bash
# 1. Test locally with production config
vllm-eval --profile production run all your-model --dry-run

# 2. Generate Kubernetes jobs from CLI config
vllm-eval config export --format k8s > evaluation-job.yaml

# 3. Deploy to Kubernetes
kubectl apply -f evaluation-job.yaml

# 4. Monitor execution
kubectl logs -f job/evaluation-job
```

---

## 📚 Framework Overview

### Evalchemy - Academic Benchmarks
**Best for**: Standard model evaluation

```bash
# Run comprehensive academic benchmarks
vllm-eval run evalchemy my-model --tasks mmlu,arc_easy,hellaswag
```

**Provides**: MMLU, ARC, HellaSwag, HumanEval accuracy metrics

### NVIDIA Eval - Mathematical Reasoning
**Best for**: Mathematical and coding capabilities

```bash
# Test mathematical reasoning
vllm-eval run nvidia my-model --benchmark aime

# Test coding capabilities  
vllm-eval run nvidia my-model --benchmark livecodebench
```

**Provides**: Problem-solving accuracy, reasoning analysis

### VLLM Benchmark - Performance Testing
**Best for**: Performance and throughput analysis

```bash
# Performance benchmarking
vllm-eval run vllm-benchmark my-model --scenario performance
```

**Provides**: TTFT, TPOT, throughput, latency metrics

### Deepeval - Custom Metrics
**Best for**: RAG evaluation and custom quality metrics

```bash
# RAG evaluation
vllm-eval run deepeval my-model --suite rag --metrics faithfulness,relevancy
```

**Provides**: Context relevance, faithfulness, custom metrics

---

## ⚡ Quick Reference

### Essential Commands

```bash
# Setup and diagnostics
vllm-eval setup                    # Initial setup wizard
vllm-eval doctor                   # System diagnostics
vllm-eval config validate          # Validate configuration

# Running evaluations
vllm-eval run evalchemy my-model   # Academic benchmarks
vllm-eval run all my-model         # All enabled frameworks
vllm-eval run all my-model --parallel  # Parallel execution

# Configuration management
vllm-eval config show             # View current config
vllm-eval config create prod      # Create new profile
vllm-eval --profile prod run ...  # Use specific profile

# Results management
vllm-eval results list            # List all results
vllm-eval results show <id>       # Show detailed results
vllm-eval results export <id>     # Export results
```

### Common Workflows

```bash
# Development workflow
vllm-eval setup
vllm-eval run evalchemy my-model --dry-run
vllm-eval run evalchemy my-model --batch-size 2
vllm-eval results show <run-id>

# Production workflow
vllm-eval --profile production config validate
vllm-eval --profile production run all my-model
vllm-eval results export <run-id> --format csv

# CI/CD workflow
vllm-eval --profile ci run evalchemy my-model --timeout 3600
vllm-eval results show <run-id> --format json > results.json
```

---

## 🔗 What's Next?

### Explore Documentation

- **[CLI Guide](../cli/overview.md)** - Comprehensive CLI documentation
- **[API Reference](../api/evalchemy-api.md)** - Framework-specific details
- **[Benchmark Configuration](benchmark-configuration.md)** - Advanced configuration
- **[Result Interpretation](result-interpretation.md)** - Understanding your results

### Advanced Usage

- **Custom Adapters**: Extend the system with your own evaluation frameworks
- **Batch Processing**: Orchestrate complex evaluation workflows
- **CI/CD Integration**: Automated evaluation in your deployment pipeline
- **Performance Tuning**: Optimize for your specific use case

### Get Help

- **Built-in Help**: `vllm-eval --help` and `vllm-eval COMMAND --help`
- **System Diagnostics**: `vllm-eval doctor --verbose`
- **Configuration Issues**: `vllm-eval config validate --test-endpoints`
- **Community**: Check project issues and discussions

---

!!! success "You're Ready!"
    
    You now have a working VLLM Evaluation setup. Start with simple evaluations using the CLI, then explore advanced features as your needs grow.
    
    **Quick Start**: `vllm-eval run evalchemy my-model`
    
    **Next**: Explore [CLI Commands](../cli/commands.md) for detailed usage patterns.