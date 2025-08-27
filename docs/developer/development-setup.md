# Development Setup

Comprehensive guide for setting up a development environment for the VLLM Evaluation System, including CLI development, framework integration, and contribution workflows.

!!! info "Development Environment"
    
    This guide covers:
    
    - 💻 **Local Development**: CLI and framework development
    - 🔧 **Tool Setup**: Required and optional development tools  
    - 🧪 **Testing**: Unit tests, integration tests, and validation
    - 🚀 **Contribution**: Code standards and submission process

## Prerequisites

### Required Tools

- **Python 3.11+** with pip
- **Docker Desktop** or **OrbStack** (for macOS)
- **Git** with GitHub access
- **Make** (usually pre-installed on macOS/Linux)

### Optional Tools (Recommended)

- **kubectl** (for Kubernetes development)
- **Helm 3+** (for chart development)
- **pre-commit** (for code quality)
- **ruff** and **mypy** (for linting and type checking)
- **BuildKit** (for advanced Docker builds)

---

## 🚀 Quick Setup (5 Minutes)

### 1. Repository Setup

```bash
# Clone and navigate
git clone https://github.com/thakicloud/vllm-eval-public.git
cd vllm-eval-public

# Setup development environment
make dev-setup

# Install CLI in development mode
pip install -e .

# Verify installation
vllm-eval --help
vllm-eval doctor
```

### 2. Development Tools Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks (optional but recommended)
pre-commit install

# Verify tools
ruff --version
mypy --version
```

### 3. Test Your Setup

```bash
# Run basic tests
make run-tests

# Test CLI functionality
vllm-eval setup --no-interactive
vllm-eval config validate
```

---

## 💻 CLI Development Workflow

### Project Structure

```
vllm_eval_cli/
├── __init__.py              # Package initialization
├── main.py                 # CLI entry point (Typer app)
├── commands/
│   ├── run.py              # Run command implementation
│   ├── config.py           # Configuration management
│   ├── system.py           # System diagnostics
│   ├── results.py          # Results management
│   └── setup.py            # Setup wizard
├── adapters/
│   ├── base.py             # Base adapter interface
│   ├── evalchemy.py        # Evalchemy integration
│   ├── nvidia.py           # NVIDIA Eval integration
│   ├── vllm_benchmark.py   # VLLM Benchmark integration
│   └── deepeval.py         # Deepeval integration
├── core/
│   └── config.py           # Configuration system
├── ui/
│   └── console.py          # Rich console utilities
└── utils/
    └── __init__.py         # Utility functions
```

### Development Patterns

#### 1. Adding New Commands

```python
# In vllm_eval_cli/commands/new_command.py
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def my_new_command(
    param: str = typer.Argument(..., help="Description"),
    option: bool = typer.Option(False, "--flag", help="Optional flag"),
) -> None:
    """Description of the new command"""
    console.print(f"[green]Executing new command with {param}[/green]")
    # Implementation here

# Register in main.py
from vllm_eval_cli.commands import new_command
app.add_typer(new_command.app, name="new-command")
```

#### 2. Creating New Adapters

```python
# In vllm_eval_cli/adapters/my_framework.py
from typing import Dict, Any, List
from .base import BaseEvaluationAdapter

class MyFrameworkAdapter(BaseEvaluationAdapter):
    """Adapter for MyFramework evaluation system"""
    
    def validate_prerequisites(self) -> bool:
        """Validate that MyFramework is available"""
        # Check dependencies, endpoints, etc.
        return True
    
    def prepare_execution(self, **kwargs) -> Dict[str, Any]:
        """Prepare execution parameters"""
        return {
            "endpoint": kwargs.get("endpoint"),
            "model_name": kwargs.get("model_name"),
            # Framework-specific params
        }
    
    def execute_evaluation(self, **kwargs) -> Dict[str, Any]:
        """Execute the actual evaluation"""
        # Implementation here
        return {"status": "success", "results": {}}
    
    def parse_results(self, raw_results: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and standardize results"""
        return {
            "framework": "my_framework",
            "metrics": {},
            "metadata": {}
        }
```

#### 3. Configuration Management

```python
# Working with configuration system
from vllm_eval_cli.core.config import ConfigManager

# Load configuration
config_manager = ConfigManager(profile="development")
config = config_manager.get_config()

# Access framework-specific settings
evalchemy_config = config.get("evaluation", {}).get("evalchemy", {})
endpoint = evalchemy_config.get("endpoint")

# Validate configuration
if config_manager.validate_config():
    console.print("[green]Configuration valid[/green]")
```

---

## 🔧 Development Environment Details

### Python Environment Setup

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -r requirements-dev.txt
pip install -r requirements-test.txt

# Install CLI in editable mode
pip install -e .
```

### Docker Development

```bash
# Build development images
make build-images

# Test specific framework containers
docker build -f docker/evalchemy.Dockerfile -t evalchemy:dev .
docker run --rm evalchemy:dev --help

# Local registry for testing
make push-images  # Pushes to local registry
```

### Kubernetes Development

```bash
# Setup local cluster
make kind-deploy

# Install development charts
helm install clickhouse charts/clickhouse --values charts/clickhouse/values.yaml
helm install grafana charts/grafana --values charts/grafana/values.yaml

# Test Kubernetes jobs
kubectl apply -f k8s/evalchemy-job.yaml
kubectl logs -f job/evalchemy-evaluation
```

---

## 🧪 Testing and Validation

### Testing Hierarchy

1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Adapter and system integration
3. **End-to-End Tests**: Complete evaluation workflows
4. **Performance Tests**: Load and benchmark testing

### Running Tests

```bash
# All tests
make run-tests

# Specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/e2e/          # End-to-end tests

# CLI-specific tests
pytest tests/cli/           # CLI command tests
pytest tests/adapters/      # Adapter tests

# With coverage
pytest --cov=vllm_eval_cli --cov-report=html
```

### Testing CLI Commands

```python
# Example CLI test
from typer.testing import CliRunner
from vllm_eval_cli.main import app

def test_cli_version():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "VLLM Evaluation CLI" in result.stdout

def test_cli_config_show():
    runner = CliRunner()
    result = runner.invoke(app, ["config", "show"])
    # Test configuration display
```

### Testing Adapters

```python
# Example adapter test
import pytest
from vllm_eval_cli.adapters.evalchemy import EvAlchemyAdapter

def test_evalchemy_adapter_validation():
    adapter = EvAlchemyAdapter()
    # Test with mock configuration
    assert adapter.validate_prerequisites()

@pytest.mark.integration
def test_evalchemy_adapter_execution():
    # Integration test with actual endpoint
    pass
```

---

## 🔍 Debugging and Profiling

### Debug Mode

```bash
# Enable debug logging
export VLLM_EVAL_DEBUG=1
vllm-eval --debug run evalchemy my-model

# Component-specific debugging
export VLLM_EVAL_DEBUG_ADAPTERS=1
export VLLM_EVAL_DEBUG_CONFIG=1
```

### Profiling Performance

```python
# Profile CLI execution
import cProfile
import pstats

def profile_command():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run CLI command
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats()
```

### Memory Monitoring

```bash
# Monitor memory usage during evaluation
memory_profiler vllm-eval run evalchemy my-model

# Check for memory leaks
valgrind --tool=memcheck python -m vllm_eval_cli.main
```

---

## 📦 Build and Distribution

### Package Building

```bash
# Build source distribution
python -m build --sdist

# Build wheel
python -m build --wheel

# Check package
twine check dist/*
```

### Container Building

```bash
# Build all images
make build-images

# Build specific framework
docker build -f docker/evalchemy.Dockerfile -t evalchemy:latest .

# Multi-platform builds
docker buildx build --platform linux/amd64,linux/arm64 .
```

### Release Process

```bash
# Tag release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Build and upload to PyPI (maintainers only)
twine upload dist/*
```

---

## ⚙️ Code Quality and Standards

### Code Formatting

```bash
# Format code with ruff
ruff format vllm_eval_cli/

# Check formatting
ruff check vllm_eval_cli/

# Fix auto-fixable issues
ruff check --fix vllm_eval_cli/
```

### Type Checking

```bash
# Run mypy type checking
mypy vllm_eval_cli/

# Check specific files
mypy vllm_eval_cli/main.py
```

### Pre-commit Hooks

```bash
# Install hooks
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Update hooks
pre-commit autoupdate
```

### Commit Message Format

```
🚀 feat(cli): add new evaluation command
⚙️ config(setup): update dependency requirements  
🐛 fix(adapters): resolve connection timeout issue
📚 docs(api): update framework integration guide
✨ improve(performance): optimize batch processing
🧪 test(integration): add end-to-end workflow tests
```

---

## 🚀 Contribution Workflow

### 1. Fork and Clone

```bash
# Fork repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/vllm-eval-public.git
cd vllm-eval-public
git remote add upstream https://github.com/thakicloud/vllm-eval-public.git
```

### 2. Create Feature Branch

```bash
# Create and switch to feature branch
git checkout -b feature/new-adapter

# Keep up to date with main
git fetch upstream
git rebase upstream/main
```

### 3. Development and Testing

```bash
# Make changes and test thoroughly
make dev-setup
vllm-eval doctor
make run-tests

# Test your specific changes
pytest tests/adapters/test_new_adapter.py -v
```

### 4. Submit Pull Request

```bash
# Commit changes
git add .
git commit -m "🚀 feat(adapters): add new framework adapter"

# Push and create PR
git push origin feature/new-adapter
# Create PR on GitHub
```

---

## 🛠️ Troubleshooting Development Issues

### Common Issues

#### 1. Import Errors

```bash
# Ensure CLI is installed in development mode
pip install -e .

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Verify package installation
pip list | grep vllm-eval
```

#### 2. Configuration Problems

```bash
# Reset configuration
rm -rf ~/.config/vllm-eval/
vllm-eval setup --force

# Validate configuration
vllm-eval config validate --test-endpoints
```

#### 3. Dependency Conflicts

```bash
# Clean environment
pip uninstall vllm-eval-cli -y
pip install -e . --force-reinstall

# Check for conflicts
pip check
```

#### 4. Docker Issues

```bash
# Reset Docker state
docker system prune -f
make build-images

# Check Docker daemon
docker info
```

### Getting Help

- **Documentation**: Check [CLI Guide](../cli/overview.md) and [API Reference](../api/evalchemy-api.md)
- **Issues**: Search existing GitHub issues
- **Debugging**: Use `vllm-eval doctor --verbose`
- **Community**: Engage in project discussions

---

## 🔗 What's Next?

### Explore Development Areas

- **[Testing Guide](testing-guide.md)** - Comprehensive testing strategies
- **[CLI Commands](../cli/commands.md)** - Understanding CLI architecture
- **[API Integration](../api/evalchemy-api.md)** - Framework-specific development
- **[Architecture Overview](../architecture/system-overview.md)** - System design

### Advanced Development

- **Custom Adapters**: Integrate new evaluation frameworks
- **Performance Optimization**: Improve evaluation speed and accuracy
- **Kubernetes Integration**: Enhance orchestration capabilities
- **Monitoring and Observability**: Add metrics and monitoring

!!! success "Development Environment Ready!"
    
    You now have a complete development setup for the VLLM Evaluation System.
    
    **Quick Test**: `vllm-eval doctor && make run-tests`
    
    **Start Developing**: Choose an area to contribute and check existing issues for ideas!