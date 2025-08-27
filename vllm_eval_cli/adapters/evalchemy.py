"""
Evalchemy Framework Adapters

This module provides adapters for integrating Evalchemy and Standard Evalchemy
evaluation frameworks into the unified CLI interface.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from vllm_eval_cli.adapters.base import ExecutionContext, ScriptBasedAdapter
from vllm_eval_cli.core.config import EvAlchemyConfig


class EvAlchemyAdapter(ScriptBasedAdapter):
    """Adapter for the main Evalchemy evaluation framework"""

    def __init__(self, config: EvAlchemyConfig):
        super().__init__(config)
        self.framework_name = "evalchemy"

    def get_script_path(self) -> Path:
        """Get the path to the Evalchemy script"""
        return Path("eval/evalchemy/run_evalchemy.sh")

    def validate_prerequisites(self) -> List[str]:
        """Validate Evalchemy prerequisites"""
        errors = super().validate_prerequisites()

        # Check if Evalchemy configuration exists
        config_path = Path("configs/eval_config.json")
        if not config_path.exists():
            errors.append(f"Evalchemy config not found: {config_path}")

        # Check Docker availability if needed
        if not self.check_docker_available():
            errors.append("Docker is required for Evalchemy but not available")

        return errors

    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """Prepare Evalchemy execution parameters"""
        model = kwargs.get("model")
        endpoint = kwargs.get("endpoint", self.config.endpoint)
        batch_size = kwargs.get("batch_size", self.config.batch_size)
        run_id = kwargs.get("run_id", self.config.run_id or context.run_id)

        # Validate required parameters
        if not model:
            raise ValueError("Model parameter is required for Evalchemy")
        if not endpoint:
            raise ValueError("Endpoint parameter is required for Evalchemy")

        return {
            "model": model,
            "endpoint": endpoint,
            "batch_size": batch_size,
            "run_id": run_id,
            "config_name": self.config.config_name,
            "output_dir": context.output_dir,
        }

    def build_command(self, context: ExecutionContext, **kwargs) -> List[str]:
        """Build the Evalchemy execution command"""
        command = [
            "bash",
            str(self.get_script_path()),
            "--endpoint", kwargs["endpoint"],
            "--batch-size", str(kwargs["batch_size"]),
            "--run-id", kwargs["run_id"],
            "--output-dir", str(kwargs["output_dir"]),
        ]

        # Add optional parameters
        if "config_name" in kwargs and kwargs["config_name"] != "default":
            command.extend(["--config", kwargs["config_name"]])

        return command

    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Parse Evalchemy results"""
        results = {
            "scores": {},
            "metadata": {},
            "output_files": [],
        }

        # Look for results in the run_id subdirectory
        run_id = kwargs.get("run_id", "")
        results_dir = output_dir / run_id if run_id else output_dir

        # Find result files
        result_files = list(results_dir.glob("*.json"))
        results["output_files"] = [str(f) for f in result_files]

        # Parse main results file if exists
        main_result_file = results_dir / "results.json"
        if main_result_file.exists():
            try:
                with open(main_result_file, "r") as f:
                    result_data = json.load(f)

                # Extract scores from Evalchemy results
                if "results" in result_data:
                    for benchmark, benchmark_results in result_data["results"].items():
                        if isinstance(benchmark_results, dict) and "score" in benchmark_results:
                            results["scores"][benchmark] = benchmark_results["score"]
                        elif isinstance(benchmark_results, (int, float)):
                            results["scores"][benchmark] = benchmark_results

                # Calculate overall score as average of all scores
                if results["scores"]:
                    results["overall_score"] = sum(results["scores"].values()) / len(results["scores"])

                # Extract metadata
                results["metadata"] = {
                    "benchmark_count": len(results["scores"]),
                    "evalchemy_version": result_data.get("version", "unknown"),
                    "config_used": result_data.get("config", {}),
                }

            except (json.JSONDecodeError, KeyError) as e:
                results["metadata"]["parse_error"] = str(e)

        return results


class StandardEvAlchemyAdapter(ScriptBasedAdapter):
    """Adapter for the Standard Evalchemy evaluation framework"""

    def __init__(self, config: EvAlchemyConfig):
        super().__init__(config)
        self.framework_name = "standard_evalchemy"

    def get_script_path(self) -> Path:
        """Get the path to the Standard Evalchemy script"""
        return Path("eval/standard_evalchemy/run_evalchemy.sh")

    def validate_prerequisites(self) -> List[str]:
        """Validate Standard Evalchemy prerequisites"""
        errors = super().validate_prerequisites()

        # Check Docker availability
        if not self.check_docker_available():
            errors.append("Docker is required for Standard Evalchemy but not available")

        # Check for standard configuration
        standard_config_path = Path("eval/standard_evalchemy/README_STANDARD.md")
        if not standard_config_path.exists():
            errors.append(f"Standard Evalchemy documentation not found: {standard_config_path}")

        return errors

    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """Prepare Standard Evalchemy execution parameters"""
        model = kwargs.get("model")
        endpoint = kwargs.get("endpoint", self.config.endpoint)
        batch_size = kwargs.get("batch_size", self.config.batch_size)
        run_id = kwargs.get("run_id", self.config.run_id or context.run_id)

        # Validate required parameters
        if not model:
            raise ValueError("Model parameter is required for Standard Evalchemy")
        if not endpoint:
            raise ValueError("Endpoint parameter is required for Standard Evalchemy")

        return {
            "model": model,
            "endpoint": endpoint,
            "batch_size": batch_size,
            "run_id": run_id,
            "output_dir": context.output_dir,
        }

    def build_command(self, context: ExecutionContext, **kwargs) -> List[str]:
        """Build the Standard Evalchemy execution command"""
        command = [
            "bash",
            str(self.get_script_path()),
            "--endpoint", kwargs["endpoint"],
            "--batch-size", str(kwargs["batch_size"]),
            "--run-id", kwargs["run_id"],
            "--output-dir", str(kwargs["output_dir"]),
        ]

        return command

    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Parse Standard Evalchemy results"""
        results = {
            "scores": {},
            "metadata": {},
            "output_files": [],
        }

        # Look for results in standardized format
        run_id = kwargs.get("run_id", "")
        results_dir = output_dir / run_id if run_id else output_dir

        # Find all JSON result files
        result_files = list(results_dir.glob("**/*.json"))
        results["output_files"] = [str(f) for f in result_files]

        # Parse standardized results
        standardized_files = list(results_dir.glob("**/standardized_*.json"))

        for std_file in standardized_files:
            try:
                with open(std_file, "r") as f:
                    std_data = json.load(f)

                # Extract benchmark name from filename
                benchmark_name = std_file.stem.replace("standardized_", "")

                # Extract scores based on standard format
                if "overall_score" in std_data:
                    results["scores"][benchmark_name] = std_data["overall_score"]
                elif "score" in std_data:
                    results["scores"][benchmark_name] = std_data["score"]
                elif "accuracy" in std_data:
                    results["scores"][benchmark_name] = std_data["accuracy"] * 100

                # Update metadata
                results["metadata"][f"{benchmark_name}_details"] = {
                    "total_questions": std_data.get("total_questions", 0),
                    "correct_answers": std_data.get("correct_answers", 0),
                    "evaluation_time": std_data.get("evaluation_time", "unknown"),
                }

            except (json.JSONDecodeError, KeyError) as e:
                results["metadata"][f"parse_error_{std_file.stem}"] = str(e)

        # Calculate overall score
        if results["scores"]:
            results["overall_score"] = sum(results["scores"].values()) / len(results["scores"])

        # Add summary metadata
        results["metadata"]["framework"] = "standard_evalchemy"
        results["metadata"]["benchmark_count"] = len(results["scores"])
        results["metadata"]["standardized_files"] = len(standardized_files)

        return results


# Factory function to create appropriate adapter
def create_evalchemy_adapter(adapter_type: str, config: EvAlchemyConfig) -> ScriptBasedAdapter:
    """
    Factory function to create the appropriate Evalchemy adapter

    Args:
        adapter_type: Type of adapter ("evalchemy" or "standard_evalchemy")
        config: Evalchemy configuration

    Returns:
        Configured adapter instance
    """
    if adapter_type.lower() == "evalchemy":
        return EvAlchemyAdapter(config)
    elif adapter_type.lower() == "standard_evalchemy":
        return StandardEvAlchemyAdapter(config)
    else:
        raise ValueError(f"Unknown Evalchemy adapter type: {adapter_type}")


# Adapter registry for easy lookup
EVALCHEMY_ADAPTERS = {
    "evalchemy": EvAlchemyAdapter,
    "standard_evalchemy": StandardEvAlchemyAdapter,
}
