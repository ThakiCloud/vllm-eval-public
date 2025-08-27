"""
NVIDIA Eval Framework Adapter

This module provides an adapter for integrating NVIDIA evaluation frameworks
including AIME and LiveCodeBench into the unified CLI interface.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from vllm_eval_cli.adapters.base import ExecutionContext, ScriptBasedAdapter
from vllm_eval_cli.core.config import NvidiaEvalConfig


class NvidiaEvalAdapter(ScriptBasedAdapter):
    """Adapter for NVIDIA evaluation frameworks (AIME, LiveCodeBench)"""

    def __init__(self, config: NvidiaEvalConfig):
        super().__init__(config)
        self.framework_name = "nvidia_eval"
        self.benchmark = config.benchmark

    def get_script_path(self) -> Path:
        """Get the path to the appropriate NVIDIA eval script"""
        script_map = {
            "aime": Path("eval/nvidia_eval/run_aime.sh"),
            "livecodebench": Path("eval/nvidia_eval/run_livecodebench.sh"),
        }

        script_path = script_map.get(self.benchmark)
        if not script_path:
            raise ValueError(f"Unknown NVIDIA benchmark: {self.benchmark}")

        return script_path

    def validate_prerequisites(self) -> List[str]:
        """Validate NVIDIA Eval prerequisites"""
        errors = super().validate_prerequisites()

        # Check if GPU is available
        if not self.check_gpu_available():
            errors.append("GPU is required for NVIDIA Eval but not available")

        # Check if model path is provided or can be inferred
        if not self.config.model_path:
            errors.append("Model path must be specified for NVIDIA Eval")

        # Check benchmark-specific requirements
        if self.benchmark == "livecodebench":
            # Check if LiveCodeBench data is available
            data_path = Path("eval/nvidia_eval/data")
            if not data_path.exists():
                errors.append(f"LiveCodeBench data directory not found: {data_path}")
        elif self.benchmark == "aime":
            # Check if AIME data is available
            aime_script = Path("eval/nvidia_eval/evaluate_aime.py")
            if not aime_script.exists():
                errors.append(f"AIME evaluation script not found: {aime_script}")

        # Check for required tools
        tools_dir = Path("eval/nvidia_eval/tools")
        if not tools_dir.exists():
            errors.append(f"NVIDIA eval tools directory not found: {tools_dir}")

        return errors

    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """Prepare NVIDIA Eval execution parameters"""
        model = kwargs.get("model")
        model_path = kwargs.get("model_path", self.config.model_path)
        gpu_count = kwargs.get("gpu_count", self.config.gpu_count)
        out_seq_len = kwargs.get("out_seq_len", self.config.out_seq_len)

        # Validate required parameters
        if not model:
            raise ValueError("Model parameter is required for NVIDIA Eval")
        if not model_path:
            raise ValueError("Model path is required for NVIDIA Eval")

        # Prepare output directory structure
        cache_dir = context.output_dir / "cache" / model
        cache_dir.mkdir(parents=True, exist_ok=True)

        return {
            "model": model,
            "model_path": model_path,
            "output_path": str(context.output_dir),
            "cache_path": str(cache_dir),
            "gpu_count": gpu_count,
            "out_seq_len": out_seq_len,
            "benchmark": self.benchmark,
        }

    def build_command(self, context: ExecutionContext, **kwargs) -> List[str]:
        """Build the NVIDIA Eval execution command"""
        # NVIDIA eval scripts use positional arguments
        command = [
            "bash",
            str(self.get_script_path()),
            kwargs["model"],           # Model name/identifier
            kwargs["cache_path"],      # Cache directory path
            str(kwargs["gpu_count"]),  # Number of GPUs
            str(kwargs["out_seq_len"])  # Output sequence length
        ]

        return command

    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Parse NVIDIA Eval results"""
        results = {
            "scores": {},
            "metadata": {},
            "output_files": [],
        }

        model = kwargs.get("model", "unknown")
        cache_dir = output_dir / "cache" / model

        # Look for standardized results
        standardized_dir = cache_dir / "standardized"
        if standardized_dir.exists():
            standardized_files = list(standardized_dir.glob("*.json"))
            results["output_files"].extend([str(f) for f in standardized_files])

            # Parse benchmark-specific results
            if self.benchmark == "aime":
                aime_file = standardized_dir / "aime_results.json"
                if aime_file.exists():
                    results.update(self._parse_aime_results(aime_file))
            elif self.benchmark == "livecodebench":
                lcb_file = standardized_dir / "livecodebench_results.json"
                if lcb_file.exists():
                    results.update(self._parse_livecodebench_results(lcb_file))

        # Look for raw results if standardized not available
        if not results["scores"]:
            raw_files = list(cache_dir.glob("**/*.json"))
            results["output_files"].extend([str(f) for f in raw_files])

            for raw_file in raw_files:
                if "aime" in raw_file.name.lower():
                    results.update(self._parse_aime_results(raw_file))
                elif "livecodebench" in raw_file.name.lower() or "lcb" in raw_file.name.lower():
                    results.update(self._parse_livecodebench_results(raw_file))

        # Add framework metadata
        results["metadata"]["framework"] = "nvidia_eval"
        results["metadata"]["benchmark"] = self.benchmark
        results["metadata"]["model"] = model

        return results

    def _parse_aime_results(self, result_file: Path) -> Dict[str, Any]:
        """Parse AIME benchmark results"""
        results = {"scores": {}, "metadata": {}}

        try:
            with open(result_file, "r") as f:
                data = json.load(f)

            # AIME results structure
            if "overall_score" in data:
                results["scores"]["aime_overall"] = data["overall_score"]
                results["overall_score"] = data["overall_score"]
            elif "accuracy" in data:
                results["scores"]["aime_accuracy"] = data["accuracy"] * 100
                results["overall_score"] = data["accuracy"] * 100
            elif "score" in data:
                results["scores"]["aime_score"] = data["score"]
                results["overall_score"] = data["score"]

            # Extract additional metrics
            if "total_problems" in data:
                results["metadata"]["total_problems"] = data["total_problems"]
            if "solved_problems" in data:
                results["metadata"]["solved_problems"] = data["solved_problems"]
            if "average_time_per_problem" in data:
                results["metadata"]["avg_time_per_problem"] = data["average_time_per_problem"]

            # Problem-level results
            if "problem_results" in data:
                problem_scores = {}
                for problem_id, problem_result in data["problem_results"].items():
                    if isinstance(problem_result, dict) and "correct" in problem_result:
                        problem_scores[f"problem_{problem_id}"] = 100 if problem_result["correct"] else 0
                results["scores"].update(problem_scores)

        except (json.JSONDecodeError, KeyError) as e:
            results["metadata"]["parse_error"] = str(e)

        return results

    def _parse_livecodebench_results(self, result_file: Path) -> Dict[str, Any]:
        """Parse LiveCodeBench results"""
        results = {"scores": {}, "metadata": {}}

        try:
            with open(result_file, "r") as f:
                data = json.load(f)

            # LiveCodeBench results structure
            if "pass_at_1" in data:
                results["scores"]["pass_at_1"] = data["pass_at_1"] * 100
                results["overall_score"] = data["pass_at_1"] * 100
            elif "overall_score" in data:
                results["scores"]["lcb_overall"] = data["overall_score"]
                results["overall_score"] = data["overall_score"]

            # Category-wise results
            if "category_results" in data:
                for category, category_result in data["category_results"].items():
                    if isinstance(category_result, dict) and "pass_at_1" in category_result:
                        results["scores"][f"{category}_pass_at_1"] = category_result["pass_at_1"] * 100
                    elif isinstance(category_result, (int, float)):
                        results["scores"][f"{category}_score"] = category_result

            # Extract metadata
            if "total_problems" in data:
                results["metadata"]["total_problems"] = data["total_problems"]
            if "solved_problems" in data:
                results["metadata"]["solved_problems"] = data["solved_problems"]
            if "contest_dates" in data:
                results["metadata"]["contest_dates"] = data["contest_dates"]
            if "languages" in data:
                results["metadata"]["languages"] = data["languages"]

            # Difficulty breakdown
            if "difficulty_breakdown" in data:
                results["metadata"]["difficulty_breakdown"] = data["difficulty_breakdown"]

        except (json.JSONDecodeError, KeyError) as e:
            results["metadata"]["parse_error"] = str(e)

        return results

    def get_supported_benchmarks(self) -> List[str]:
        """Get list of supported NVIDIA benchmarks"""
        return ["aime", "livecodebench"]

    def set_benchmark(self, benchmark: str) -> None:
        """Set the benchmark to use"""
        if benchmark not in self.get_supported_benchmarks():
            raise ValueError(f"Unsupported benchmark: {benchmark}. Supported: {self.get_supported_benchmarks()}")
        self.benchmark = benchmark
        self.config.benchmark = benchmark


# Factory function for creating NVIDIA adapters
def create_nvidia_adapter(benchmark: str, config: NvidiaEvalConfig) -> NvidiaEvalAdapter:
    """
    Factory function to create NVIDIA adapter for specific benchmark

    Args:
        benchmark: Benchmark name ("aime" or "livecodebench")
        config: NVIDIA eval configuration

    Returns:
        Configured NVIDIA adapter instance
    """
    # Update config with benchmark
    config.benchmark = benchmark
    return NvidiaEvalAdapter(config)


# Supported benchmarks registry
NVIDIA_BENCHMARKS = {
    "aime": "AIME (American Invitational Mathematics Examination)",
    "livecodebench": "LiveCodeBench (Live Coding Benchmark)",
}
