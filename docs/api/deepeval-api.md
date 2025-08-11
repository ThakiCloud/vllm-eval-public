# Deepeval API

Deepeval is a comprehensive evaluation framework specifically designed for Large Language Models (LLMs), providing pytest-style unit testing capabilities for AI applications. It offers 30+ built-in metrics and supports both RAG (Retrieval-Augmented Generation) and end-to-end evaluation scenarios.

!!! info "Framework Overview"
    
    Deepeval provides:
    
    - **30+ Built-in Metrics**: Comprehensive evaluation across multiple dimensions
    - **RAG Evaluation**: Specialized metrics for retrieval-augmented generation
    - **Custom Metrics**: Extensible framework for domain-specific evaluations
    - **Pytest Integration**: Familiar testing patterns for AI applications

## Prerequisites

!!! warning "Setup Requirements"
    
    Before using Deepeval, ensure you have:
    
    - Python 3.8+ environment
    - Required dependencies installed via `requirements-dev.txt`
    - A running VLLM server endpoint
    - Access to evaluation datasets

## Installation & Setup

### Install Dependencies

```bash
pip install -r requirements-dev.txt
```

### Configuration

Deepeval uses configuration files located in `configs/`:

- `deepeval.yaml`: Main configuration for evaluation parameters
- `pytest.ini`: Pytest-specific settings

!!! tip "Configuration Files"
    
    Review and customize the configuration files in the `configs/` directory to match your evaluation requirements and model specifications.

## Core Evaluation Metrics

Deepeval provides several categories of evaluation metrics:

### RAG-Specific Metrics

!!! info "RAG Evaluation"
    
    For Retrieval-Augmented Generation systems, Deepeval offers specialized metrics:

- **Context Relevance**: Measures how relevant retrieved context is to the query
- **Hallucination Detection**: Identifies generated content not supported by context  
- **RAG Precision**: Evaluates accuracy of responses given the retrieved context
- **Context Utilization**: Assesses how effectively the model uses provided context

### General LLM Metrics

- **Semantic Similarity**: Compares generated text with reference answers
- **Toxicity Detection**: Identifies harmful or inappropriate content
- **Bias Evaluation**: Measures potential biases in model outputs
- **Factual Consistency**: Verifies factual accuracy of generated content

## Running Deepeval Tests

### Basic Test Execution

Navigate to the deepeval tests directory and run evaluations:

```bash
cd eval/deepeval_tests
pytest test_llm_rag.py -v
```

### Custom Metric Testing

Run tests with custom metrics:

```bash
pytest test_custom_metric.py -v --model-endpoint http://localhost:8000/v1
```

!!! note "Test Structure"
    
    Deepeval tests are located in `eval/deepeval_tests/` and follow pytest conventions:
    
    ```
    eval/deepeval_tests/
    ├── __init__.py
    ├── metrics/              # Custom metric definitions
    ├── test_custom_metric.py # Custom metric tests
    └── test_llm_rag.py      # RAG evaluation tests
    ```

### Running Specific Metrics

Execute targeted evaluations:

```bash
# Run only RAG precision tests
pytest test_llm_rag.py::test_rag_precision -v

# Run hallucination detection
pytest test_llm_rag.py::test_hallucination_detection -v
```

## Custom Metrics Development

### Creating Custom Metrics

Deepeval supports custom metric development. Create new metrics in the `metrics/` directory:

```python
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

class CustomRelevanceMetric(BaseMetric):
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
    
    def measure(self, test_case: LLMTestCase) -> float:
        # Implement your custom evaluation logic
        pass
    
    def is_successful(self) -> bool:
        return self.score >= self.threshold
```

!!! tip "Metric Development"
    
    When developing custom metrics:
    
    - Inherit from `BaseMetric` base class
    - Implement `measure()` method for scoring logic
    - Define success criteria via `is_successful()`
    - Add comprehensive error handling

### Registering Custom Metrics

Register your custom metrics in the test files:

```python
from metrics.custom_relevance import CustomRelevanceMetric

def test_custom_relevance():
    metric = CustomRelevanceMetric(threshold=0.8)
    test_case = LLMTestCase(
        input="Your test input",
        actual_output="Model's actual output",
        expected_output="Expected output"
    )
    metric.measure(test_case)
    assert metric.is_successful()
```

## Docker Integration

### Building Deepeval Container

```bash
docker build -f docker/deepeval.Dockerfile -t deepeval-runner:latest .
```

### Running Containerized Evaluations

```bash
docker run --rm \
    --network host \
    -e VLLM_ENDPOINT="http://localhost:8000/v1" \
    -e EVALUATION_CONFIG='{"metrics": ["rag_precision", "hallucination"], "threshold": 0.7}' \
    -v $(pwd)/eval/deepeval_tests/results:/workspace/results \
    deepeval-runner:latest
```

!!! warning "Docker Networking"
    
    Use `--network host` to ensure the container can access your local VLLM server endpoint.

## Advanced Configuration

### Evaluation Parameters

Configure evaluation behavior in `deepeval.yaml`:

```yaml
evaluation:
  model_endpoint: "http://localhost:8000/v1"
  batch_size: 10
  timeout: 300
  metrics:
    rag_precision:
      threshold: 0.8
      strict_mode: true
    hallucination:
      threshold: 0.3
      detection_model: "gpt-4"
```

### Parallel Execution

Run evaluations in parallel for improved performance:

```bash
pytest test_llm_rag.py -n 4 --dist=loadfile
```

!!! success "Performance Optimization"
    
    For large-scale evaluations:
    
    - Use parallel execution with `-n` flag
    - Implement batching for API calls
    - Configure appropriate timeouts
    - Monitor resource usage during evaluation

## Output & Results

### Test Results Structure

Deepeval generates comprehensive evaluation reports:

```
eval/deepeval_tests/results/
├── test_results.json         # Aggregated test results
├── detailed_metrics.json     # Per-metric breakdown
├── failed_cases.json         # Failed test cases for analysis
└── performance_stats.json    # Execution performance metrics
```

### Interpreting Results

!!! info "Result Analysis"
    
    Deepeval results include:
    
    - **Overall Score**: Aggregated performance across all metrics
    - **Per-Metric Scores**: Individual metric performance
    - **Pass/Fail Status**: Binary success indicators
    - **Confidence Intervals**: Statistical confidence measures
    - **Error Analysis**: Detailed failure case information

## Integration with VLLM Eval Pipeline

Deepeval integrates seamlessly with the broader VLLM evaluation ecosystem:

```bash
# Integration with aggregation pipeline
python scripts/aggregate_metrics.py --include-deepeval --results-dir eval/deepeval_tests/results
```

!!! note "Pipeline Integration"
    
    Deepeval results are automatically compatible with the VLLM evaluation aggregation system and can be included in comprehensive model performance reports.
