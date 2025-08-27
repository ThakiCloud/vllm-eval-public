"""
Adapter Registry for VLLM Evaluation CLI

This module provides a centralized registry for all evaluation framework adapters,
making it easy to discover, create, and manage different adapters.
"""

from typing import Dict, Type, Union

from vllm_eval_cli.adapters.base import BaseEvaluationAdapter
from vllm_eval_cli.adapters.evalchemy import EvAlchemyAdapter, StandardEvAlchemyAdapter
from vllm_eval_cli.adapters.nvidia import NvidiaEvalAdapter
from vllm_eval_cli.adapters.vllm_benchmark import VLLMBenchmarkAdapter
from vllm_eval_cli.adapters.deepeval import DeepevalAdapter
from vllm_eval_cli.core.config import (
    EvAlchemyConfig,
    NvidiaEvalConfig,
    VLLMBenchmarkConfig,
    DeepevalConfig,
    ConfigManager,
)


# Adapter class registry
ADAPTER_REGISTRY: Dict[str, Type[BaseEvaluationAdapter]] = {
    "evalchemy": EvAlchemyAdapter,
    "standard_evalchemy": StandardEvAlchemyAdapter,
    "nvidia": NvidiaEvalAdapter,
    "vllm_benchmark": VLLMBenchmarkAdapter,
    "deepeval": DeepevalAdapter,
}


# Configuration class mapping
CONFIG_MAPPING = {
    "evalchemy": EvAlchemyConfig,
    "standard_evalchemy": EvAlchemyConfig,
    "nvidia": NvidiaEvalConfig,
    "vllm_benchmark": VLLMBenchmarkConfig,
    "deepeval": DeepevalConfig,
}


def get_available_adapters() -> Dict[str, str]:
    """Get a dictionary of available adapters with descriptions"""
    return {
        "evalchemy": "Evalchemy benchmark evaluation framework",
        "standard_evalchemy": "Standard Evalchemy evaluation framework",
        "nvidia": "NVIDIA evaluation suite (AIME, LiveCodeBench)",
        "vllm_benchmark": "VLLM performance benchmarking",
        "deepeval": "Deepeval testing framework",
    }


def create_adapter(
    framework: str,
    config_manager: ConfigManager,
    **kwargs
) -> BaseEvaluationAdapter:
    """
    Create an adapter instance for the specified framework

    Args:
        framework: Framework name (must be in ADAPTER_REGISTRY)
        config_manager: Configuration manager instance
        **kwargs: Additional parameters for adapter configuration

    Returns:
        Configured adapter instance

    Raises:
        ValueError: If framework is not supported
    """
    if framework not in ADAPTER_REGISTRY:
        available = ", ".join(ADAPTER_REGISTRY.keys())
        raise ValueError(f"Unknown framework: {framework}. Available: {available}")

    # Get framework configuration
    framework_config = config_manager.get_framework_config(framework)

    # Override configuration with kwargs if provided
    if kwargs:
        config_dict = framework_config.dict()
        config_dict.update(kwargs)
        config_class = CONFIG_MAPPING[framework]
        framework_config = config_class(**config_dict)

    # Create adapter instance
    adapter_class = ADAPTER_REGISTRY[framework]
    return adapter_class(framework_config)


def validate_all_adapters(config_manager: ConfigManager) -> Dict[str, list]:
    """
    Validate all available adapters

    Args:
        config_manager: Configuration manager instance

    Returns:
        Dictionary mapping framework names to lists of validation errors
    """
    validation_results = {}

    for framework in ADAPTER_REGISTRY.keys():
        try:
            adapter = create_adapter(framework, config_manager)
            validation_results[framework] = adapter.validate_prerequisites()
        except Exception as e:
            validation_results[framework] = [f"Failed to create adapter: {e}"]

    return validation_results


def get_adapter_info(framework: str, config_manager: ConfigManager) -> Dict[str, any]:
    """
    Get detailed information about a specific adapter

    Args:
        framework: Framework name
        config_manager: Configuration manager instance

    Returns:
        Dictionary with adapter information
    """
    if framework not in ADAPTER_REGISTRY:
        raise ValueError(f"Unknown framework: {framework}")

    try:
        adapter = create_adapter(framework, config_manager)
        return adapter.get_framework_info()
    except Exception as e:
        return {
            "name": framework,
            "error": str(e),
            "status": "error"
        }


# Export commonly used items
__all__ = [
    "ADAPTER_REGISTRY",
    "CONFIG_MAPPING",
    "get_available_adapters",
    "create_adapter",
    "validate_all_adapters",
    "get_adapter_info",
]
