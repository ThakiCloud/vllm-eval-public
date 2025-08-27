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
    print_error,
    print_warning,
    prompt_input,
    prompt_yes_no,
    prompt_choice,
)


def setup_wizard(interactive: bool = True, force: bool = False) -> None:
    """Run the interactive setup wizard"""
    print_header("VLLM Evaluation CLI Setup Wizard", "Welcome! Let's configure your evaluation environment.")

    if not interactive:
        print_info("Running non-interactive setup with defaults...")
        config_manager = ConfigManager()
        # Set basic defaults for non-interactive mode
        config_manager.config.default_endpoint = "http://localhost:8000/v1"
        config_manager.config.system.results_dir = Path("./results")
        try:
            config_manager.save_config()
            print_success("✅ Basic configuration created with defaults!")
            return
        except Exception as e:
            print_info(f"❌ Failed to save configuration: {e}")
            raise typer.Exit(1)

    # Initialize configuration manager
    config_manager = ConfigManager()
    
    # Check for existing configuration
    if config_manager.config_file.exists() and not force:
        overwrite = prompt_yes_no(
            f"Configuration already exists at {config_manager.config_file}. Overwrite?",
            default=False
        )
        if not overwrite:
            print_info("Setup cancelled. Use --force to overwrite existing configuration.")
            return

    print_info("🔧 Basic Configuration")

    # Default endpoint with validation
    while True:
        endpoint = prompt_input(
            "Default model endpoint URL",
            default="http://localhost:8000/v1",
            required=True
        )
        if endpoint and (endpoint.startswith("http://") or endpoint.startswith("https://")):
            config_manager.config.default_endpoint = endpoint
            break
        else:
            print_info("⚠️ Please enter a valid HTTP/HTTPS URL")

    # Default model
    model = prompt_input(
        "Default model name (optional)",
        default=None
    )
    if model:
        config_manager.config.default_model = model

    # Results directory with validation
    while True:
        results_dir = prompt_input(
            "Results directory",
            default="./results",
            required=True
        )
        if results_dir:
            try:
                from pathlib import Path
                results_path = Path(results_dir)
                results_path.mkdir(parents=True, exist_ok=True)
                config_manager.config.system.results_dir = results_path
                break
            except Exception as e:
                print_info(f"⚠️ Cannot create directory '{results_dir}': {e}")

    # Batch size configuration
    batch_size = prompt_input(
        "Default batch size for evaluations",
        default="8",
    )
    if batch_size and batch_size.isdigit():
        config_manager.config.system.default_batch_size = int(batch_size)

    print_info("📊 Framework Configuration")

    # Configure frameworks with better descriptions
    frameworks = {
        "evalchemy": "Evalchemy - Comprehensive benchmark suite (MMLU, HumanEval, etc.)",
        "standard_evalchemy": "Standard Evalchemy - Standardized evaluation pipeline", 
        "nvidia": "NVIDIA Eval - Mathematical reasoning (AIME, LiveCodeBench)",
        "vllm_benchmark": "VLLM Benchmark - Performance and throughput testing",
        "deepeval": "Deepeval - Custom metrics and RAG evaluation"
    }

    enabled_count = 0
    for framework, description in frameworks.items():
        enabled = prompt_yes_no(
            f"Enable {description}?",
            default=True
        )

        framework_config = config_manager.get_framework_config(framework)
        framework_config.enabled = enabled
        if enabled:
            enabled_count += 1
    
    if enabled_count == 0:
        print_info("⚠️ Warning: No frameworks enabled. You can enable them later using 'vllm-eval config'")

    # Advanced options
    if prompt_yes_no("Configure advanced options (timeouts, logging)?", default=False):
        timeout = prompt_input(
            "Default timeout for evaluations (seconds)",
            default="3600",
        )
        if timeout and timeout.isdigit():
            config_manager.config.system.default_timeout = int(timeout)
        
        log_level = prompt_choice(
            "Default log level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO"
        )
        if log_level:
            config_manager.config.system.log_level = log_level

    # Save configuration
    try:
        config_manager.save_config()
        print_success("✅ Configuration saved successfully!")
        print_info(f"📁 Configuration file: {config_manager.config_file}")
        print_info(f"📊 Enabled frameworks: {enabled_count}")
        print_info(f"💾 Results directory: {config_manager.config.system.results_dir}")
        print_info("")
        print_success("🚀 Setup complete! Next steps:")
        print_info("  • Test configuration: [bold]vllm-eval doctor[/bold]")
        print_info("  • Quick evaluation: [bold]vllm-eval run quick <model-name>[/bold]")
        print_info("  • View all commands: [bold]vllm-eval --help[/bold]")
    except Exception as e:
        print_info(f"❌ Failed to save configuration: {e}")
        raise typer.Exit(1)


def setup_dependencies(frameworks: list[str]) -> None:
    """Setup dependencies for specific frameworks"""
    print_header("Dependency Setup", "Installing required packages for evaluation frameworks")
    
    dependency_map = {
        "evalchemy": ["lm-eval[all]", "torch", "transformers", "datasets"],
        "deepeval": ["deepeval", "torch", "transformers", "nltk"],
        "nvidia": ["torch", "transformers", "numpy", "pandas", "scikit-learn"],
        "vllm_benchmark": ["vllm", "aiohttp", "tenacity"],
        "all": ["vllm-eval[full]"]
    }
    
    import subprocess
    import sys
    
    for framework in frameworks:
        if framework not in dependency_map:
            print_warning(f"Unknown framework: {framework}")
            continue
            
        packages = dependency_map[framework]
        print_info(f"📦 Installing packages for {framework}: {', '.join(packages)}")
        
        for package in packages:
            try:
                print_info(f"Installing {package}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                print_success(f"✓ {package} installed successfully")
            except subprocess.CalledProcessError as e:
                print_error(f"❌ Failed to install {package}: {e}")
    
    print_success("🎉 Dependency setup completed!")
