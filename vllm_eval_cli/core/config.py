"""
Configuration Management System for VLLM Evaluation CLI

This module provides comprehensive configuration management including:
- TOML-based configuration files
- Profile support for different environments
- Environment variable integration
- Configuration validation and defaults
- Dynamic configuration loading and saving
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import toml
from pydantic import BaseModel, Field, validator
from rich.console import Console

from vllm_eval_cli.ui.console import create_console

console = create_console()


class EvalFrameworkConfig(BaseModel):
    """Configuration for evaluation frameworks"""

    enabled: bool = Field(True, description="Whether this framework is enabled")
    endpoint: Optional[str] = Field(None, description="API endpoint URL")
    batch_size: int = Field(1, description="Batch size for evaluations")
    timeout: int = Field(3600, description="Timeout in seconds")
    gpu_count: int = Field(1, description="Number of GPUs to use")
    max_workers: int = Field(4, description="Maximum parallel workers")

    @validator("batch_size")
    def validate_batch_size(cls, v):
        if v < 1:
            raise ValueError("Batch size must be at least 1")
        return v

    @validator("timeout")
    def validate_timeout(cls, v):
        if v < 1:
            raise ValueError("Timeout must be at least 1 second")
        return v


class EvAlchemyConfig(EvalFrameworkConfig):
    """Configuration specific to EvAlchemy framework"""

    config_name: str = Field("default", description="EvAlchemy configuration name")
    run_id: Optional[str] = Field(None, description="Custom run ID")
    output_format: str = Field("json", description="Output format")

    class Config:
        extra = "allow"


class NvidiaEvalConfig(EvalFrameworkConfig):
    """Configuration specific to NVIDIA Eval framework"""

    benchmark: str = Field("livecodebench", description="Benchmark to run")
    out_seq_len: int = Field(2048, description="Output sequence length")
    model_path: Optional[str] = Field(None, description="Path to model")

    @validator("benchmark")
    def validate_benchmark(cls, v):
        valid_benchmarks = ["livecodebench", "aime"]
        if v not in valid_benchmarks:
            raise ValueError(f"Benchmark must be one of: {valid_benchmarks}")
        return v


class VLLMBenchmarkConfig(EvalFrameworkConfig):
    """Configuration specific to VLLM Benchmark framework"""

    scenario: str = Field("performance", description="Benchmark scenario")
    concurrency: int = Field(10, description="Concurrency level")
    duration: int = Field(300, description="Test duration in seconds")

    @validator("scenario")
    def validate_scenario(cls, v):
        valid_scenarios = ["performance", "stress_test", "latency", "throughput"]
        if v not in valid_scenarios:
            raise ValueError(f"Scenario must be one of: {valid_scenarios}")
        return v


class DeepevalConfig(EvalFrameworkConfig):
    """Configuration specific to Deepeval framework"""

    test_suite: str = Field("default", description="Test suite to run")
    metrics: List[str] = Field(["precision", "recall"], description="Metrics to evaluate")

    @validator("metrics")
    def validate_metrics(cls, v):
        valid_metrics = ["precision", "recall", "f1", "accuracy", "bleu", "rouge"]
        for metric in v:
            if metric not in valid_metrics:
                raise ValueError(f"Metric '{metric}' not in valid metrics: {valid_metrics}")
        return v


class SystemConfig(BaseModel):
    """System-wide configuration"""

    results_dir: Path = Field(Path("./results"), description="Results output directory")
    logs_dir: Path = Field(Path("./logs"), description="Logs directory")
    cache_dir: Path = Field(Path("./cache"), description="Cache directory")
    temp_dir: Path = Field(Path("/tmp/vllm-eval"), description="Temporary files directory")
    max_log_files: int = Field(10, description="Maximum number of log files to keep")
    log_level: str = Field("INFO", description="Logging level")

    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v.upper()


class CLIConfig(BaseModel):
    """Main CLI configuration"""

    # System configuration
    system: SystemConfig = Field(default_factory=SystemConfig)

    # Framework configurations
    evalchemy: EvAlchemyConfig = Field(default_factory=EvAlchemyConfig)
    standard_evalchemy: EvAlchemyConfig = Field(default_factory=EvAlchemyConfig)
    nvidia_eval: NvidiaEvalConfig = Field(default_factory=NvidiaEvalConfig)
    vllm_benchmark: VLLMBenchmarkConfig = Field(default_factory=VLLMBenchmarkConfig)
    deepeval: DeepevalConfig = Field(default_factory=DeepevalConfig)

    # Global settings
    default_model: Optional[str] = Field(None, description="Default model to use")
    default_endpoint: str = Field("http://localhost:8000/v1", description="Default API endpoint")
    parallel_execution: bool = Field(False, description="Enable parallel execution")

    class Config:
        extra = "forbid"
        validate_assignment = True


class ConfigManager:
    """Configuration manager for the VLLM Evaluation CLI"""

    def __init__(
        self,
        config_file: Optional[Path] = None,
        profile: Optional[str] = None,
    ):
        self.profile = profile or "default"
        self.config_file = config_file or self._get_default_config_path()
        self.config: CLIConfig = CLIConfig()

        # Load configuration
        self._load_config()
        self._apply_environment_overrides()

    def _get_default_config_path(self) -> Path:
        """Get the default configuration file path"""
        # Try XDG config directory first
        xdg_config = os.environ.get("XDG_CONFIG_HOME")
        if xdg_config:
            config_dir = Path(xdg_config) / "vllm-eval"
        else:
            config_dir = Path.home() / ".config" / "vllm-eval"

        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / f"{self.profile}.toml"

    def _load_config(self) -> None:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r") as f:
                    config_data = toml.load(f)
                self.config = CLIConfig(**config_data)
                console.print(f"[green]✅ Configuration loaded from {self.config_file}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Error loading config: {e}[/yellow]")
                console.print("[yellow]Using default configuration[/yellow]")
        else:
            console.print(f"[yellow]⚠️  Config file not found: {self.config_file}[/yellow]")
            console.print("[yellow]Using default configuration[/yellow]")

    def _apply_environment_overrides(self) -> None:
        """Apply environment variable overrides"""
        env_mappings = {
            "VLLM_EVAL_ENDPOINT": ("default_endpoint",),
            "VLLM_EVAL_MODEL": ("default_model",),
            "VLLM_EVAL_RESULTS_DIR": ("system", "results_dir"),
            "VLLM_EVAL_LOG_LEVEL": ("system", "log_level"),
            "VLLM_EVAL_PARALLEL": ("parallel_execution",),
        }

        for env_var, config_path in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                self._set_nested_config(self.config, config_path, value)

    def _set_nested_config(self, config: Any, path: tuple, value: str) -> None:
        """Set a nested configuration value"""
        current = config
        for key in path[:-1]:
            current = getattr(current, key)

        # Type conversion based on field type
        field_info = current.__fields__[path[-1]]
        if field_info.type_ == bool:
            value = value.lower() in ("true", "1", "yes", "on")
        elif field_info.type_ == int:
            value = int(value)
        elif field_info.type_ == Path:
            value = Path(value)

        setattr(current, path[-1], value)

    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                toml.dump(self.config.dict(), f)
            console.print(f"[green]✅ Configuration saved to {self.config_file}[/green]")
        except Exception as e:
            console.print(f"[red]❌ Error saving config: {e}[/red]")
            raise

    def get_framework_config(self, framework: str) -> EvalFrameworkConfig:
        """Get configuration for a specific framework"""
        framework_map = {
            "evalchemy": self.config.evalchemy,
            "standard_evalchemy": self.config.standard_evalchemy,
            "nvidia": self.config.nvidia_eval,
            "vllm_benchmark": self.config.vllm_benchmark,
            "deepeval": self.config.deepeval,
        }

        if framework not in framework_map:
            raise ValueError(f"Unknown framework: {framework}")

        return framework_map[framework]

    def list_profiles(self) -> List[str]:
        """List available configuration profiles"""
        config_dir = self.config_file.parent
        if not config_dir.exists():
            return []

        profiles = []
        for file in config_dir.glob("*.toml"):
            if file.stem != "default":
                profiles.append(file.stem)

        return sorted(profiles)

    def create_profile(self, name: str, base_profile: Optional[str] = None) -> None:
        """Create a new configuration profile"""
        if base_profile:
            base_config_file = self.config_file.parent / f"{base_profile}.toml"
            if base_config_file.exists():
                with open(base_config_file, "r") as f:
                    config_data = toml.load(f)
                base_config = CLIConfig(**config_data)
            else:
                raise ValueError(f"Base profile '{base_profile}' not found")
        else:
            base_config = CLIConfig()

        new_config_file = self.config_file.parent / f"{name}.toml"
        with open(new_config_file, "w") as f:
            toml.dump(base_config.dict(), f)

        console.print(f"[green]✅ Profile '{name}' created[/green]")

    def delete_profile(self, name: str) -> None:
        """Delete a configuration profile"""
        if name == "default":
            raise ValueError("Cannot delete default profile")

        profile_file = self.config_file.parent / f"{name}.toml"
        if profile_file.exists():
            profile_file.unlink()
            console.print(f"[green]✅ Profile '{name}' deleted[/green]")
        else:
            raise ValueError(f"Profile '{name}' not found")

    def validate_config(self) -> List[str]:
        """Validate the current configuration and return any issues"""
        issues = []

        # Validate directories exist or can be created
        dirs_to_check = [
            self.config.system.results_dir,
            self.config.system.logs_dir,
            self.config.system.cache_dir,
        ]

        for dir_path in dirs_to_check:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                issues.append(f"Cannot create directory {dir_path}: {e}")

        # Validate framework configurations
        frameworks = ["evalchemy", "standard_evalchemy", "nvidia_eval", "vllm_benchmark", "deepeval"]
        for framework in frameworks:
            try:
                self.get_framework_config(framework)
            except Exception as e:
                issues.append(f"Invalid {framework} configuration: {e}")

        return issues

    def get_config_summary(self) -> Dict[str, Any]:
        """Get a summary of the current configuration"""
        return {
            "profile": self.profile,
            "config_file": str(self.config_file),
            "default_model": self.config.default_model,
            "default_endpoint": self.config.default_endpoint,
            "parallel_execution": self.config.parallel_execution,
            "results_dir": str(self.config.system.results_dir),
            "enabled_frameworks": {
                framework: getattr(self.config, framework).enabled
                for framework in ["evalchemy", "standard_evalchemy", "nvidia_eval", "vllm_benchmark", "deepeval"]
            },
        }
