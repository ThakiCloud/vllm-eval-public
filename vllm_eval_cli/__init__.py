"""
VLLM Evaluation CLI - Unified Command Line Interface for VLLM Model Evaluation

This package provides a comprehensive CLI tool for managing and executing various
evaluation frameworks including Evalchemy, NVIDIA Eval, VLLM Benchmark, and Deepeval.

The CLI offers:
- Unified interface for all evaluation systems
- Rich terminal output with progress indicators
- Configuration management with profiles
- Batch processing capabilities
- Interactive setup and monitoring
"""

__version__ = "0.1.0"
__title__ = "vllm-eval-cli"
__description__ = "Unified Command Line Interface for VLLM Model Evaluation"
__author__ = "VLLM Eval Team"
__author_email__ = "vllm-eval@company.com"
__license__ = "Apache-2.0"

# Export main CLI application
from .main import app as cli_app

__all__ = ["cli_app", "__version__"]
