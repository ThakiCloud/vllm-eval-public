"""
Deepeval Framework Adapter

This module provides an adapter for integrating Deepeval testing framework
into the unified CLI interface. It supports various test suites and metrics
for LLM evaluation including RAG, custom metrics, and functional testing.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

from vllm_eval_cli.adapters.base import BaseEvaluationAdapter, ExecutionContext, EvaluationResult
from vllm_eval_cli.core.config import DeepevalConfig


class DeepevalAdapter(BaseEvaluationAdapter):
    """Adapter for Deepeval testing framework"""

    def __init__(self, config: DeepevalConfig):
        super().__init__(config)
        self.framework_name = "deepeval"
        self.test_suite = config.test_suite
        self.metrics = config.metrics

    def validate_prerequisites(self) -> List[str]:
        """Validate Deepeval prerequisites"""
        errors = []

        # Check if Python is available
        try:
            result = subprocess.run([sys.executable, "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                errors.append("Python interpreter not available")
        except FileNotFoundError:
            errors.append("Python interpreter not found")

        # Check if deepeval package is installed
        try:
            import deepeval
        except ImportError:
            errors.append("Deepeval package not installed. Run: pip install deepeval")

        # Check if pytest is available
        try:
            result = subprocess.run([sys.executable, "-m", "pytest", "--version"], capture_output=True, text=True)
            if result.returncode != 0:
                errors.append("Pytest not available")
        except FileNotFoundError:
            errors.append("Pytest not found")

        # Check if test files exist
        test_dir = Path("eval/deepeval_tests")
        if not test_dir.exists():
            errors.append(f"Deepeval tests directory not found: {test_dir}")
        else:
            # Check for specific test files
            test_files = list(test_dir.glob("test_*.py"))
            if not test_files:
                errors.append(f"No test files found in {test_dir}")

        # Check if configuration file exists
        config_file = Path("configs/deepeval.yaml")
        if not config_file.exists():
            errors.append(f"Deepeval config file not found: {config_file}")

        return errors

    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """Prepare Deepeval execution parameters"""
        model = kwargs.get("model")
        test_suite = kwargs.get("test_suite", self.test_suite)
        metrics = kwargs.get("metrics", self.metrics)
        endpoint = kwargs.get("endpoint", self.config.endpoint)

        # Validate required parameters
        if not model:
            raise ValueError("Model parameter is required for Deepeval")

        # Determine test files to run
        test_files = self._get_test_files(test_suite)
        if not test_files:
            raise ValueError(f"No test files found for test suite: {test_suite}")

        return {
            "model": model,
            "test_suite": test_suite,
            "metrics": metrics,
            "test_files": test_files,
            "endpoint": endpoint,
            "results_dir": str(context.output_dir),
        }

    def execute_evaluation(
        self,
        context: ExecutionContext,
        prepared_params: Dict[str, Any],
        **kwargs
    ) -> EvaluationResult:
        """Execute Deepeval tests"""
        from datetime import datetime

        result = EvaluationResult(
            run_id=context.run_id,
            framework=self.framework_name,
            model=prepared_params["model"],
            benchmark=prepared_params["test_suite"],
            start_time=datetime.now(),
            status="running"
        )

        try:
            # Set environment variables for deepeval
            import os
            env = os.environ.copy()
            env.update({
                "DEEPEVAL_MODEL": prepared_params["model"],
                "DEEPEVAL_ENDPOINT": prepared_params.get("endpoint", ""),
                "DEEPEVAL_RESULTS_DIR": prepared_params["results_dir"],
                "DEEPEVAL_METRICS": ",".join(prepared_params["metrics"]),
            })

            # Build pytest command
            pytest_args = [
                sys.executable, "-m", "pytest",
                "--verbose",
                "--tb=short",
                f"--junitxml={context.output_dir}/deepeval_results.xml",
                f"--html={context.output_dir}/deepeval_report.html",
                "--self-contained-html",
            ]

            # Add test files
            for test_file in prepared_params["test_files"]:
                pytest_args.append(str(test_file))

            # Add custom pytest configurations
            config_file = Path("configs/pytest.ini")
            if config_file.exists():
                pytest_args.extend(["-c", str(config_file)])

            # Execute tests
            with open(context.log_file, "w") as log_file:
                process_result = subprocess.run(
                    pytest_args,
                    cwd=Path.cwd(),
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=self.config.timeout
                )

            # Pytest exit codes: 0 = all tests passed, 1 = some tests failed, others = errors
            if process_result.returncode == 0:
                result.status = "success"
            elif process_result.returncode == 1:
                result.status = "partial_success"  # Some tests failed but ran successfully
            else:
                raise subprocess.CalledProcessError(
                    process_result.returncode,
                    pytest_args,
                    None,
                    f"Deepeval tests failed with exit code {process_result.returncode}"
                )

        except subprocess.TimeoutExpired:
            result.status = "error"
            result.error_message = f"Tests timed out after {self.config.timeout} seconds"

        except subprocess.CalledProcessError as e:
            result.status = "error"
            result.error_message = f"Test execution failed: {e}"

        return result

    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """Parse Deepeval test results"""
        results = {
            "scores": {},
            "metadata": {},
            "output_files": [],
        }

        # Parse JUnit XML results
        junit_file = output_dir / "deepeval_results.xml"
        if junit_file.exists():
            results["output_files"].append(str(junit_file))
            results.update(self._parse_junit_results(junit_file))

        # Parse HTML report
        html_file = output_dir / "deepeval_report.html"
        if html_file.exists():
            results["output_files"].append(str(html_file))

        # Parse deepeval-specific results
        deepeval_results = list(output_dir.glob("**/deepeval_*.json"))
        for result_file in deepeval_results:
            results["output_files"].append(str(result_file))
            try:
                with open(result_file, "r") as f:
                    data = json.load(f)
                results.update(self._parse_deepeval_results(data, result_file.stem))
            except (json.JSONDecodeError, Exception) as e:
                results["metadata"][f"parse_error_{result_file.stem}"] = str(e)

        # Parse metric-specific results
        for metric in self.metrics:
            metric_file = output_dir / f"{metric}_results.json"
            if metric_file.exists():
                results["output_files"].append(str(metric_file))
                try:
                    with open(metric_file, "r") as f:
                        data = json.load(f)
                    results["scores"][f"{metric}_score"] = data.get("score", 0)
                except (json.JSONDecodeError, Exception) as e:
                    results["metadata"][f"parse_error_{metric}"] = str(e)

        # Calculate overall score
        if results["scores"]:
            # For deepeval, use average of all metric scores
            metric_scores = [v for k, v in results["scores"].items() if "score" in k and isinstance(v, (int, float))]
            if metric_scores:
                results["overall_score"] = sum(metric_scores) / len(metric_scores)

        # Add framework metadata
        results["metadata"]["framework"] = "deepeval"
        results["metadata"]["test_suite"] = kwargs.get("test_suite", self.test_suite)
        results["metadata"]["metrics"] = self.metrics

        return results

    def _get_test_files(self, test_suite: str) -> List[Path]:
        """Get test files for the specified test suite"""
        test_dir = Path("eval/deepeval_tests")

        if test_suite == "all":
            return list(test_dir.glob("test_*.py"))
        elif test_suite == "rag":
            return list(test_dir.glob("test_*rag*.py"))
        elif test_suite == "custom":
            return list(test_dir.glob("test_custom*.py"))
        elif test_suite == "llm":
            return list(test_dir.glob("test_*llm*.py"))
        else:
            # Look for specific test file
            specific_file = test_dir / f"test_{test_suite}.py"
            if specific_file.exists():
                return [specific_file]

            # Look for files containing the test suite name
            matching_files = list(test_dir.glob(f"test_*{test_suite}*.py"))
            return matching_files

    def _parse_junit_results(self, junit_file: Path) -> Dict[str, Any]:
        """Parse JUnit XML results"""
        results = {"scores": {}, "metadata": {}}

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(junit_file)
            root = tree.getroot()

            # Extract test suite information
            testsuite = root.find("testsuite")
            if testsuite is not None:
                total_tests = int(testsuite.get("tests", 0))
                failures = int(testsuite.get("failures", 0))
                errors = int(testsuite.get("errors", 0))
                skipped = int(testsuite.get("skipped", 0))

                passed_tests = total_tests - failures - errors - skipped

                results["scores"]["total_tests"] = total_tests
                results["scores"]["passed_tests"] = passed_tests
                results["scores"]["failed_tests"] = failures
                results["scores"]["error_tests"] = errors
                results["scores"]["skipped_tests"] = skipped

                # Calculate pass rate
                if total_tests > 0:
                    pass_rate = (passed_tests / total_tests) * 100
                    results["scores"]["pass_rate"] = pass_rate
                    results["overall_score"] = pass_rate

                # Extract execution time
                time_str = testsuite.get("time")
                if time_str:
                    results["metadata"]["execution_time_seconds"] = float(time_str)

            # Extract individual test results
            test_cases = root.findall(".//testcase")
            test_results = {}

            for testcase in test_cases:
                test_name = testcase.get("name", "unknown")
                test_class = testcase.get("classname", "")

                # Check if test passed, failed, or had error
                if testcase.find("failure") is not None:
                    test_results[test_name] = "failed"
                elif testcase.find("error") is not None:
                    test_results[test_name] = "error"
                elif testcase.find("skipped") is not None:
                    test_results[test_name] = "skipped"
                else:
                    test_results[test_name] = "passed"

            results["metadata"]["test_results"] = test_results

        except Exception as e:
            results["metadata"]["junit_parse_error"] = str(e)

        return results

    def _parse_deepeval_results(self, data: Dict[str, Any], file_prefix: str) -> Dict[str, Any]:
        """Parse deepeval-specific results"""
        results = {"scores": {}, "metadata": {}}

        # Extract evaluation metrics
        if "test_results" in data:
            for test_name, test_result in data["test_results"].items():
                if isinstance(test_result, dict):
                    for metric_name, metric_value in test_result.items():
                        if isinstance(metric_value, (int, float)):
                            results["scores"][f"{test_name}_{metric_name}"] = metric_value

        # Extract summary metrics
        if "summary" in data:
            summary = data["summary"]
            if isinstance(summary, dict):
                for key, value in summary.items():
                    if isinstance(value, (int, float)):
                        results["scores"][f"summary_{key}"] = value

        # Extract individual metric scores
        for metric in self.metrics:
            if metric in data:
                metric_data = data[metric]
                if isinstance(metric_data, (int, float)):
                    results["scores"][f"{metric}_score"] = metric_data
                elif isinstance(metric_data, dict) and "score" in metric_data:
                    results["scores"][f"{metric}_score"] = metric_data["score"]

        return results

    def get_available_test_suites(self) -> List[str]:
        """Get list of available test suites"""
        test_dir = Path("eval/deepeval_tests")
        if not test_dir.exists():
            return []

        test_files = list(test_dir.glob("test_*.py"))
        suites = {"all", "rag", "custom", "llm"}  # Built-in suites

        # Extract suite names from filenames
        for test_file in test_files:
            name = test_file.stem.replace("test_", "")
            if "_" in name:
                suite_name = name.split("_")[0]
                suites.add(suite_name)
            suites.add(name)

        return sorted(list(suites))

    def get_available_metrics(self) -> List[str]:
        """Get list of available metrics"""
        return [
            "precision", "recall", "f1", "accuracy",
            "bleu", "rouge", "bertscore",
            "toxicity", "bias", "hallucination",
            "faithfulness", "answer_relevancy",
            "context_precision", "context_recall"
        ]


# Factory function for creating Deepeval adapters
def create_deepeval_adapter(test_suite: str, metrics: List[str], config: DeepevalConfig) -> DeepevalAdapter:
    """
    Factory function to create Deepeval adapter for specific test suite and metrics

    Args:
        test_suite: Test suite name
        metrics: List of metrics to evaluate
        config: Deepeval configuration

    Returns:
        Configured Deepeval adapter instance
    """
    # Update config with parameters
    config.test_suite = test_suite
    config.metrics = metrics
    return DeepevalAdapter(config)


# Supported test suites and metrics
DEEPEVAL_TEST_SUITES = {
    "all": "Run all available tests",
    "rag": "RAG (Retrieval-Augmented Generation) tests",
    "custom": "Custom metric tests",
    "llm": "General LLM evaluation tests",
}

DEEPEVAL_METRICS = {
    "precision": "Precision metric",
    "recall": "Recall metric",
    "f1": "F1 score metric",
    "accuracy": "Accuracy metric",
    "bleu": "BLEU score for text generation",
    "rouge": "ROUGE score for summarization",
    "bertscore": "BERTScore for semantic similarity",
    "toxicity": "Toxicity detection",
    "bias": "Bias detection",
    "hallucination": "Hallucination detection",
    "faithfulness": "Faithfulness to source",
    "answer_relevancy": "Answer relevancy",
    "context_precision": "Context precision",
    "context_recall": "Context recall",
}
