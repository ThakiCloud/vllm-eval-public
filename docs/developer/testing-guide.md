# Testing Guide

Comprehensive testing strategies for the VLLM Evaluation System, covering CLI components, framework adapters, and end-to-end workflows.

!!! info "Testing Philosophy"
    
    - 🧪 **Test Pyramid**: Unit → Integration → E2E testing approach
    - ⚙️ **CLI Testing**: Command validation and user experience testing
    - 🔌 **Adapter Testing**: Framework integration and compatibility testing
    - 🚀 **Automation**: CI/CD integration and regression prevention

## Testing Architecture

### Test Categories

```
Testing Pyramid:

    ┌──────────────────┐
    │      E2E Tests      │  <- Full workflows, real endpoints
    ├──────────────────┤
    │  Integration Tests   │  <- Adapter + framework integration
    ├──────────────────┤
    │      Unit Tests      │  <- CLI commands, config, utilities
    └──────────────────┘
```

---

## 🧪 Unit Testing

### CLI Command Testing

```python
# tests/unit/test_cli_commands.py
from typer.testing import CliRunner
from vllm_eval_cli.main import app

def test_version_command():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "VLLM Evaluation CLI" in result.stdout

def test_config_show():
    runner = CliRunner()
    with mock_config():
        result = runner.invoke(app, ["config", "show"])
        assert result.exit_code == 0
        assert "profile_name" in result.stdout

def test_run_dry_run():
    runner = CliRunner()
    result = runner.invoke(app, [
        "run", "evalchemy", "test-model", "--dry-run"
    ])
    assert result.exit_code == 0
    assert "Would execute" in result.stdout
```

### Configuration Testing

```python
# tests/unit/test_config.py
from vllm_eval_cli.core.config import ConfigManager

def test_config_loading():
    config_manager = ConfigManager()
    config = config_manager.get_config()
    assert "profile_name" in config
    
def test_config_validation():
    config_manager = ConfigManager()
    assert config_manager.validate_config()

def test_profile_switching():
    config_manager = ConfigManager(profile="test")
    config = config_manager.get_config()
    assert config["profile_name"] == "test"
```

### Running Unit Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test categories
pytest tests/unit/test_cli_commands.py -v
pytest tests/unit/test_config.py -v

# With coverage
pytest tests/unit/ --cov=vllm_eval_cli --cov-report=html
```

---

## 🔌 Integration Testing

### Adapter Testing

```python
# tests/integration/test_adapters.py
import pytest
from vllm_eval_cli.adapters.evalchemy import EvAlchemyAdapter

class TestEvAlchemyAdapter:
    def setup_method(self):
        self.adapter = EvAlchemyAdapter()
    
    def test_prerequisite_validation(self):
        assert self.adapter.validate_prerequisites()
    
    @pytest.mark.integration
    def test_execution_with_mock_server(self):
        with mock_vllm_server():
            result = self.adapter.execute_evaluation(
                model_name="test-model",
                endpoint="http://localhost:8000/v1",
                tasks=["arc_easy"],
                limit=5
            )
            assert result["status"] == "success"
            assert "metrics" in result
```

### Framework Integration Testing

```python
# tests/integration/test_framework_integration.py
@pytest.mark.integration
def test_evalchemy_integration():
    """Test actual Evalchemy execution with mock server"""
    with MockVLLMServer() as server:
        result = run_cli_command([
            "run", "evalchemy", "test-model",
            "--endpoint", server.url,
            "--tasks", "arc_easy",
            "--limit", "5"
        ])
        assert result.exit_code == 0
        assert "Evaluation completed" in result.output

@pytest.mark.integration
def test_multiple_frameworks():
    """Test running multiple frameworks"""
    with MockVLLMServer() as server:
        result = run_cli_command([
            "run", "all", "test-model",
            "--frameworks", "evalchemy,deepeval",
            "--endpoint", server.url
        ])
        assert result.exit_code == 0
```

---

## 🚀 End-to-End Testing

### Full Workflow Testing

```python
# tests/e2e/test_evaluation_workflows.py
@pytest.mark.e2e
@pytest.mark.slow
def test_complete_evaluation_workflow():
    """Test complete evaluation from setup to results"""
    # Setup
    with temporary_config() as config_dir:
        # Initialize CLI
        run_setup_wizard(config_dir)
        
        # Run evaluation
        result = run_evaluation(
            framework="evalchemy",
            model="test-model",
            config_dir=config_dir
        )
        
        # Verify results
        assert result.success
        assert result.results_file.exists()
        
        # Verify result format
        results = load_results(result.results_file)
        assert "metadata" in results
        assert "metrics" in results
```

### Performance Testing

```python
# tests/performance/test_performance.py
@pytest.mark.performance
def test_evaluation_performance():
    """Test evaluation performance metrics"""
    import time
    
    start_time = time.time()
    
    with MockVLLMServer() as server:
        result = run_cli_command([
            "run", "evalchemy", "test-model",
            "--endpoint", server.url,
            "--tasks", "arc_easy",
            "--batch-size", "4"
        ])
    
    duration = time.time() - start_time
    
    # Performance assertions
    assert result.exit_code == 0
    assert duration < 300  # Should complete within 5 minutes
    
    # Memory usage checks
    assert server.peak_memory_mb < 1000
```

---

## 🛠️ Test Infrastructure

### Mock Server Setup

```python
# tests/utils/mock_server.py
import threading
import time
from flask import Flask, request, jsonify

class MockVLLMServer:
    def __init__(self, port=8000):
        self.port = port
        self.app = Flask(__name__)
        self._setup_routes()
        
    def _setup_routes(self):
        @self.app.route("/health")
        def health():
            return {"status": "ok"}
            
        @self.app.route("/v1/completions", methods=["POST"])
        def completions():
            data = request.json
            return {
                "id": "mock-completion",
                "object": "text_completion",
                "choices": [{
                    "text": "Mock response",
                    "index": 0,
                    "finish_reason": "length"
                }]
            }
    
    def __enter__(self):
        self.thread = threading.Thread(
            target=self.app.run,
            kwargs={"host": "localhost", "port": self.port}
        )
        self.thread.start()
        time.sleep(0.1)  # Wait for server to start
        return self
    
    def __exit__(self, *args):
        # Cleanup server
        pass
```

### Test Configuration Management

```python
# tests/conftest.py
import pytest
import tempfile
from pathlib import Path

@pytest.fixture
def temp_config_dir():
    """Create temporary configuration directory"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)

@pytest.fixture
def mock_config():
    """Provide mock configuration"""
    return {
        "profile_name": "test",
        "model": {
            "name": "test-model",
            "endpoint": "http://localhost:8000/v1"
        },
        "evaluation": {
            "evalchemy": {"enabled": True}
        }
    }
```

---

## 🚀 CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements-dev.txt
        pip install -e .
    
    - name: Run unit tests
      run: pytest tests/unit/ -v --cov=vllm_eval_cli
    
    - name: Run integration tests
      run: pytest tests/integration/ -v -m integration
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
- repo: local
  hooks:
  - id: pytest-unit
    name: Run unit tests
    entry: pytest tests/unit/
    language: python
    pass_filenames: false
    always_run: true
    
  - id: pytest-cli
    name: Run CLI tests
    entry: pytest tests/unit/test_cli_commands.py -v
    language: python
    pass_filenames: false
    files: ^vllm_eval_cli/
```

---

## ⚙️ Test Execution

### Running Test Suites

```bash
# Quick unit tests
make test-unit

# Integration tests (requires Docker)
make test-integration

# Full test suite
make test-all

# Performance tests
make test-performance

# Specific framework tests
pytest tests/ -k "evalchemy" -v
pytest tests/ -k "nvidia" -v

# Tests with markers
pytest tests/ -m "unit" -v
pytest tests/ -m "integration" -v
pytest tests/ -m "e2e" -v --slow
```

### Test Configuration

```ini
# pytest.ini
[tool:pytest]
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    performance: Performance tests
    
addopts = -v --strict-markers --tb=short
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

---

## 📊 Quality Metrics

### Coverage Requirements

- **Unit Tests**: ≥ 90% code coverage
- **Integration Tests**: ≥ 80% adapter coverage
- **E2E Tests**: ≥ 70% workflow coverage

### Test Performance Targets

- **Unit Tests**: < 30 seconds total
- **Integration Tests**: < 5 minutes total
- **E2E Tests**: < 30 minutes total

### Quality Gates

```bash
# Coverage check
pytest --cov=vllm_eval_cli --cov-fail-under=90

# Performance check
pytest tests/performance/ --benchmark-only

# Security check
bandit -r vllm_eval_cli/
```

---

## 📚 Best Practices

### Test Organization

1. **Mirror source structure** in test directories
2. **Use descriptive test names** that explain intent
3. **Group related tests** in classes
4. **Use fixtures** for common setup
5. **Mock external dependencies** appropriately

### Test Writing Guidelines

```python
# Good test example
def test_evalchemy_adapter_executes_with_valid_config():
    """Test that EvAlchemy adapter executes successfully with valid configuration"""
    # Arrange
    adapter = EvAlchemyAdapter()
    config = {"endpoint": "http://localhost:8000", "tasks": ["arc_easy"]}
    
    # Act
    result = adapter.execute_evaluation(**config)
    
    # Assert
    assert result["status"] == "success"
    assert "metrics" in result
    assert len(result["metrics"]) > 0
```

### Continuous Testing

```bash
# Watch mode for development
pytest-watch -- tests/unit/

# Automated testing on file changes
find . -name "*.py" | entr -c pytest tests/unit/
```

!!! success "Testing Excellence"
    
    Comprehensive testing ensures reliable CLI functionality and smooth user experience.
    
    **Remember**: Test early, test often, and maintain high coverage for critical components.