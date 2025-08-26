"""
Setup Command Module

This module implements the setup wizard for initial configuration
of the VLLM Evaluation CLI system.
"""

import typer

from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import (
    print_header,
    print_info,
    print_success,
    prompt_input,
    prompt_yes_no,
    prompt_choice,
)


def setup_wizard(interactive: bool = True, force: bool = False) -> None:
    """Run the interactive setup wizard"""
    print_header("VLLM Evaluation CLI Setup Wizard", "Welcome! Let's configure your evaluation environment.")

    if not interactive:
        print_info("Non-interactive setup not yet implemented")
        return

    # Initialize configuration manager
    config_manager = ConfigManager()

    print_info("🔧 Basic Configuration")

    # Default endpoint
    endpoint = prompt_input(
        "Default model endpoint URL",
        default="http://localhost:8000/v1",
        required=True
    )
    if endpoint:
        config_manager.config.default_endpoint = endpoint

    # Default model
    model = prompt_input(
        "Default model name (optional)",
        default=None
    )
    if model:
        config_manager.config.default_model = model

    # Results directory
    results_dir = prompt_input(
        "Results directory",
        default="./results",
        required=True
    )
    if results_dir:
        from pathlib import Path
        config_manager.config.system.results_dir = Path(results_dir)

    print_info("📊 Framework Configuration")

    # Configure frameworks
    frameworks = {
        "evalchemy": "Evalchemy benchmark evaluation",
        "standard_evalchemy": "Standard Evalchemy evaluation",
        "nvidia": "NVIDIA evaluation suite",
        "vllm_benchmark": "VLLM performance benchmarking",
        "deepeval": "Deepeval testing framework"
    }

    for framework, description in frameworks.items():
        enabled = prompt_yes_no(
            f"Enable {framework} ({description})?",
            default=True
        )

        framework_config = config_manager.get_framework_config(framework)
        framework_config.enabled = enabled

    # Save configuration
    try:
        config_manager.save_config()
        print_success("✅ Configuration saved successfully!")
        print_info(f"📁 Configuration file: {config_manager.config_file}")
        print_info("🚀 You can now use 'vllm-eval run --help' to get started!")
    except Exception as e:
        print_info(f"❌ Failed to save configuration: {e}")
        raise typer.Exit(1)
