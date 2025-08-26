"""
VLLM Benchmark Framework Adapter

This module provides an adapter for integrating VLLM performance benchmarking
into the unified CLI interface. It supports various benchmark scenarios including
performance, stress testing, latency, and throughput measurements.
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from vllm_eval_cli.adapters.base import BaseEvaluationAdapter, ExecutionContext, EvaluationResult
from vllm_eval_cli.core.config import VLLMBenchmarkConfig


class VLLMBenchmarkAdapter(BaseEvaluationAdapter):
    """Adapter for VLLM performance benchmarking"""

    def __init__(self, config: VLLMBenchmarkConfig):
        super().__init__(config)
        self.framework_name = "vllm_benchmark"
        self.scenario = config.scenario

    def validate_prerequisites(self) -> List[str]:
        """Validate VLLM Benchmark prerequisites"""
        errors = []

        # Check if Docker is available
        if not self.check_docker_available():
            errors.append("Docker is required for VLLM Benchmark but not available")

        # Check if benchmark scripts exist
        script_paths = [
            Path("eval/vllm-benchmark/run_vllm_benchmark.sh"),
            Path("eval/vllm-benchmark/run_vllm_performance_benchmark.sh"),
        ]

        script_found = False
        for script_path in script_paths:
            if script_path.exists():
                script_found = True
                break

        if not script_found:
            errors.append(f"VLLM benchmark scripts not found in: {[str(p) for p in script_paths]}")

        # Check if analysis script exists
        analysis_script = Path("eval/vllm-benchmark/analyze_vllm_results.py")
        if not analysis_script.exists():
            errors.append(f"VLLM results analysis script not found: {analysis_script}")

        return errors

    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """Prepare VLLM Benchmark execution parameters"""
        model = kwargs.get("model")
        endpoint = kwargs.get("endpoint", self.config.endpoint or "http://localhost:8000")
        concurrency = kwargs.get("concurrency", self.config.concurrency)
        duration = kwargs.get("duration", self.config.duration)
        scenario = kwargs.get("scenario", self.scenario)

        # Validate required parameters
        if not model:
            raise ValueError("Model parameter is required for VLLM Benchmark")
        if not endpoint:
            raise ValueError("Endpoint parameter is required for VLLM Benchmark")

        # Validate scenario
        valid_scenarios = ["performance", "stress_test", "latency", "throughput"]
        if scenario not in valid_scenarios:
            raise ValueError(f"Invalid scenario: {scenario}. Valid options: {valid_scenarios}")

        # Prepare performance results directory
        perf_results_dir = context.output_dir / "performance"
        perf_results_dir.mkdir(parents=True, exist_ok=True)

        return {
            "model": model,
            "endpoint": endpoint,
            "concurrency": concurrency,
            "duration": duration,
            "scenario": scenario,
            "results_dir": str(perf_results_dir),
            "model_name": model.split("/")[-1] if "/" in model else model,
        }

    def execute_evaluation(
        self,
        context: ExecutionContext,
        prepared_params: Dict[str, Any],
        **kwargs
    ) -> EvaluationResult:
        """Execute VLLM Benchmark evaluation"""
        result = EvaluationResult(
            run_id=context.run_id,
            framework=self.framework_name,
            model=prepared_params["model"],
            benchmark=prepared_params["scenario"],
            start_time=context.start_time if hasattr(context, 'start_time') else None,
            status="running"
        )

        try:
            # Set environment variables for the benchmark
            env = os.environ.copy()
            env.update({
                "VLLM_ENDPOINT": prepared_params["endpoint"],
                "MODEL_NAME": prepared_params["model_name"],
                "MAX_CONCURRENCY": str(prepared_params["concurrency"]),
                "DURATION": str(prepared_params["duration"]),
                "RESULTS_DIR": prepared_params["results_dir"],
                "SCENARIO": prepared_params["scenario"],
            })

            # Determine which script to run based on scenario
            if prepared_params["scenario"] in ["performance", "stress_test"]:
                script_path = Path("eval/vllm-benchmark/run_vllm_performance_benchmark.sh")
            else:
                script_path = Path("eval/vllm-benchmark/run_vllm_benchmark.sh")

            # Build Docker command for benchmark execution
            docker_command = [
                "docker", "run",
                "--rm",
                "--network", "host",
                "-v", f"{prepared_params['results_dir']}:/app/results",
                "-e", f"VLLM_ENDPOINT={prepared_params['endpoint']}",
                "-e", f"MODEL_NAME={prepared_params['model_name']}",
                "-e", f"MAX_CONCURRENCY={prepared_params['concurrency']}",
                "-e", f"DURATION={prepared_params['duration']}",
                "vllm-benchmark:latest"
            ]

            # Execute benchmark
            with open(context.log_file, "w") as log_file:
                if script_path.exists():
                    # Use script if available
                    process_result = subprocess.run(
                        ["bash", str(script_path)],
                        env=env,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=self.config.timeout
                    )
                else:
                    # Use Docker command directly
                    process_result = subprocess.run(
                        docker_command,
                        stdout=log_file,
                        stderr=subprocess.STDOUT,
                        text=True,
                        timeout=self.config.timeout
                    )

            if process_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    process_result.returncode,
                    "VLLM Benchmark",
                    None,
                    f"Benchmark execution failed with exit code {process_result.returncode}"
                )

            result.status = "success"

        except subprocess.TimeoutExpired:
            result.status = "error"
            result.error_message = f"Benchmark timed out after {self.config.timeout} seconds"

        except subprocess.CalledProcessError as e:
            result.status = "error"
            result.error_message = f"Benchmark execution failed: {e}"

        return result

    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Parse VLLM Benchmark results"""
        results = {
            "scores": {},
            "metadata": {},
            "output_files": [],
        }

        # Look for performance results
        perf_dir = output_dir / "performance"
        if not perf_dir.exists():
            perf_dir = output_dir

        # Find result files
        result_files = list(perf_dir.glob("**/*.json"))
        csv_files = list(perf_dir.glob("**/*.csv"))

        results["output_files"] = [str(f) for f in result_files + csv_files]

        # Parse JSON results
        for result_file in result_files:
            try:
                with open(result_file, "r") as f:
                    data = json.load(f)

                # Extract performance metrics
                self._extract_performance_metrics(data, results, result_file.stem)

            except (json.JSONDecodeError, Exception) as e:
                results["metadata"][f"parse_error_{result_file.stem}"] = str(e)

        # Parse standardized results if available
        standardized_file = perf_dir / "standardized_results.json"
        if standardized_file.exists():
            try:
                with open(standardized_file, "r") as f:
                    std_data = json.load(f)

                if "performance_metrics" in std_data:
                    results["scores"].update(std_data["performance_metrics"])

                if "overall_score" in std_data:
                    results["overall_score"] = std_data["overall_score"]

            except (json.JSONDecodeError, Exception) as e:
                results["metadata"]["standardized_parse_error"] = str(e)

        # Calculate overall score if not already set
        if "overall_score" not in results and results["scores"]:
            # For performance benchmarks, use throughput as primary metric
            if "throughput_tokens_per_second" in results["scores"]:
                results["overall_score"] = results["scores"]["throughput_tokens_per_second"]
            elif "requests_per_second" in results["scores"]:
                results["overall_score"] = results["scores"]["requests_per_second"]
            else:
                # Use average of all numeric scores
                numeric_scores = [v for v in results["scores"].values() if isinstance(v, (int, float))]
                if numeric_scores:
                    results["overall_score"] = sum(numeric_scores) / len(numeric_scores)

        # Add framework metadata
        results["metadata"]["framework"] = "vllm_benchmark"
        results["metadata"]["scenario"] = kwargs.get("scenario", self.scenario)
        results["metadata"]["total_result_files"] = len(result_files)

        return results

    def _extract_performance_metrics(self, data: Dict[str, Any], results: Dict[str, Any], file_prefix: str) -> None:
        """Extract performance metrics from benchmark data"""
        # Common performance metrics
        metric_mappings = {
            "throughput": "throughput_tokens_per_second",
            "tokens_per_second": "throughput_tokens_per_second",
            "requests_per_second": "requests_per_second",
            "latency": "avg_latency_ms",
            "average_latency": "avg_latency_ms",
            "p50_latency": "p50_latency_ms",
            "p95_latency": "p95_latency_ms",
            "p99_latency": "p99_latency_ms",
            "ttft": "time_to_first_token_ms",
            "time_to_first_token": "time_to_first_token_ms",
            "tpot": "time_per_output_token_ms",
            "time_per_output_token": "time_per_output_token_ms",
            "total_requests": "total_requests",
            "successful_requests": "successful_requests",
            "failed_requests": "failed_requests",
            "error_rate": "error_rate_percent",
        }

        # Extract metrics with prefix
        for key, value in data.items():
            if isinstance(value, (int, float)):
                # Map known metrics
                if key.lower() in metric_mappings:
                    metric_name = metric_mappings[key.lower()]
                    results["scores"][metric_name] = value
                else:
                    # Include with file prefix
                    results["scores"][f"{file_prefix}_{key}"] = value
            elif isinstance(value, dict):
                # Recursively extract from nested dictionaries
                self._extract_performance_metrics(value, results, f"{file_prefix}_{key}")

        # Extract summary statistics
        if "summary" in data:
            summary = data["summary"]
            if isinstance(summary, dict):
                for key, value in summary.items():
                    if isinstance(value, (int, float)):
                        results["scores"][f"summary_{key}"] = value

        # Extract benchmark configuration
        if "config" in data:
            config = data["config"]
            if isinstance(config, dict):
                results["metadata"][f"{file_prefix}_config"] = config

    def get_supported_scenarios(self) -> List[str]:
        """Get list of supported benchmark scenarios"""
        return ["performance", "stress_test", "latency", "throughput"]

    def set_scenario(self, scenario: str) -> None:
        """Set the benchmark scenario"""
        if scenario not in self.get_supported_scenarios():
            raise ValueError(f"Unsupported scenario: {scenario}. Supported: {self.get_supported_scenarios()}")
        self.scenario = scenario
        self.config.scenario = scenario


# Factory function for creating VLLM benchmark adapters
def create_vllm_benchmark_adapter(scenario: str, config: VLLMBenchmarkConfig) -> VLLMBenchmarkAdapter:
    """
    Factory function to create VLLM benchmark adapter for specific scenario

    Args:
        scenario: Benchmark scenario name
        config: VLLM benchmark configuration

    Returns:
        Configured VLLM benchmark adapter instance
    """
    # Update config with scenario
    config.scenario = scenario
    return VLLMBenchmarkAdapter(config)


# Supported scenarios registry
VLLM_SCENARIOS = {
    "performance": "General performance benchmark",
    "stress_test": "High-load stress testing",
    "latency": "Latency-focused testing",
    "throughput": "Throughput-focused testing",
}
