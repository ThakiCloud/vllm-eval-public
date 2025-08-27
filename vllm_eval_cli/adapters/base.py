"""
Base adapter interface and common functionality for evaluation frameworks

This module provides the foundation for integrating different evaluation frameworks
into the unified CLI interface. It defines common interfaces, execution patterns,
and standardized result formats.
"""

import json
import subprocess
import tempfile
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from vllm_eval_cli.core.config import EvalFrameworkConfig
from vllm_eval_cli.ui.console import console, create_progress, print_error, print_info, print_success


class EvaluationResult(BaseModel):
    """Standardized evaluation result format"""

    # Metadata
    run_id: str = Field(..., description="Unique identifier for this evaluation run")
    framework: str = Field(..., description="Name of the evaluation framework")
    model: str = Field(..., description="Model name or identifier")
    benchmark: Optional[str] = Field(None, description="Benchmark or test suite name")

    # Timing information
    start_time: datetime = Field(..., description="Evaluation start time")
    end_time: Optional[datetime] = Field(None, description="Evaluation end time")
    duration_seconds: Optional[float] = Field(None, description="Total duration in seconds")

    # Results
    status: str = Field(..., description="Execution status: success, error, cancelled")
    overall_score: Optional[float] = Field(None, description="Overall score (0-100)")
    detailed_scores: Dict[str, float] = Field(default_factory=dict, description="Detailed scores by metric")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Error information
    error_message: Optional[str] = Field(None, description="Error message if status is error")
    error_details: Optional[Dict[str, Any]] = Field(None, description="Detailed error information")

    # Files and outputs
    output_files: List[str] = Field(default_factory=list, description="List of output file paths")
    log_file: Optional[str] = Field(None, description="Path to execution log file")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ExecutionContext(BaseModel):
    """Context information for evaluation execution"""

    run_id: str
    output_dir: Path
    temp_dir: Path
    log_file: Path
    dry_run: bool = False
    verbose: bool = False

    def create_directories(self) -> None:
        """Create necessary directories"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)


class BaseEvaluationAdapter(ABC):
    """
    Abstract base class for evaluation framework adapters

    This class defines the common interface that all evaluation framework
    adapters must implement. It provides shared functionality for execution,
    logging, and result standardization.
    """

    def __init__(self, config: EvalFrameworkConfig):
        self.config = config
        self.framework_name = self.__class__.__name__.replace("Adapter", "").lower()

    @abstractmethod
    def validate_prerequisites(self) -> List[str]:
        """
        Validate that all prerequisites for this framework are met

        Returns:
            List of validation error messages (empty if all valid)
        """
        pass

    @abstractmethod
    def prepare_execution(self, context: ExecutionContext, **kwargs) -> Dict[str, Any]:
        """
        Prepare for evaluation execution

        Args:
            context: Execution context with directories and settings
            **kwargs: Framework-specific parameters

        Returns:
            Dictionary of prepared execution parameters
        """
        pass

    @abstractmethod
    def execute_evaluation(
        self,
        context: ExecutionContext,
        prepared_params: Dict[str, Any],
        **kwargs
    ) -> EvaluationResult:
        """
        Execute the evaluation

        Args:
            context: Execution context
            prepared_params: Parameters from prepare_execution
            **kwargs: Additional runtime parameters

        Returns:
            Standardized evaluation result
        """
        pass

    @abstractmethod
    def parse_results(self, output_dir: Path, **kwargs) -> Dict[str, Any]:
        """
        Parse framework-specific results into standardized format

        Args:
            output_dir: Directory containing evaluation outputs
            **kwargs: Additional parsing parameters

        Returns:
            Dictionary of parsed results
        """
        pass

    def run_evaluation(
        self,
        model: str,
        output_dir: Optional[Path] = None,
        run_id: Optional[str] = None,
        dry_run: bool = False,
        verbose: bool = False,
        **kwargs
    ) -> EvaluationResult:
        """
        Main entry point for running an evaluation

        This method orchestrates the entire evaluation process from validation
        through execution to result parsing.
        """
        # Generate run ID if not provided
        if not run_id:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = f"{self.framework_name}_{model}_{timestamp}"

        # Set up directories
        if not output_dir:
            output_dir = Path("./results") / run_id

        temp_dir = Path(tempfile.gettempdir()) / "vllm-eval" / run_id
        log_file = output_dir / f"{self.framework_name}.log"

        # Create execution context
        context = ExecutionContext(
            run_id=run_id,
            output_dir=output_dir,
            temp_dir=temp_dir,
            log_file=log_file,
            dry_run=dry_run,
            verbose=verbose
        )

        # Create directories
        context.create_directories()

        # Initialize result object
        result = EvaluationResult(
            run_id=run_id,
            framework=self.framework_name,
            model=model,
            start_time=datetime.now(),
            status="running"
        )

        try:
            # Validate prerequisites
            print_info(f"Validating prerequisites for {self.framework_name}")
            validation_errors = self.validate_prerequisites()
            if validation_errors:
                raise ValueError(f"Validation failed: {'; '.join(validation_errors)}")

            # Prepare execution
            print_info(f"Preparing {self.framework_name} evaluation")
            prepared_params = self.prepare_execution(context, model=model, **kwargs)

            if dry_run:
                print_info("Dry run mode - skipping actual execution")
                result.status = "dry_run"
                result.metadata["prepared_params"] = prepared_params
                return result

            # Execute evaluation
            print_info(f"Executing {self.framework_name} evaluation")
            result = self.execute_evaluation(context, prepared_params, model=model, **kwargs)

            # Parse results
            print_info(f"Parsing {self.framework_name} results")
            parsed_results = self.parse_results(context.output_dir, **kwargs)

            # Update result with parsed data
            result.detailed_scores.update(parsed_results.get("scores", {}))
            result.overall_score = parsed_results.get("overall_score")
            result.metadata.update(parsed_results.get("metadata", {}))
            result.output_files = parsed_results.get("output_files", [])

            result.status = "success"
            print_success(f"{self.framework_name} evaluation completed successfully")

        except KeyboardInterrupt:
            result.status = "cancelled"
            result.error_message = "Evaluation cancelled by user"
            print_error("Evaluation cancelled by user")

        except Exception as e:
            result.status = "error"
            result.error_message = str(e)
            result.error_details = {"exception_type": type(e).__name__}
            print_error(f"Evaluation failed: {e}")

            if verbose:
                console.print_exception()

        finally:
            # Finalize result
            result.end_time = datetime.now()
            if result.start_time and result.end_time:
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()

            result.log_file = str(context.log_file)

            # Save result to file
            result_file = context.output_dir / "result.json"
            with open(result_file, "w") as f:
                json.dump(result.dict(), f, indent=2, default=str)

            # Clean up temp directory if not in debug mode
            if not verbose and context.temp_dir.exists():
                import shutil
                shutil.rmtree(context.temp_dir, ignore_errors=True)

        return result

    def run_command(
        self,
        command: Union[str, List[str]],
        cwd: Optional[Path] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command with proper logging and error handling

        Args:
            command: Command to execute (string or list)
            cwd: Working directory
            env: Environment variables
            timeout: Command timeout in seconds
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess object with execution results
        """
        # Convert string command to list
        if isinstance(command, str):
            command_list = command.split()
        else:
            command_list = command

        # Set timeout from config if not provided
        if timeout is None:
            timeout = self.config.timeout

        print_info(f"Executing: {' '.join(command_list)}")

        try:
            result = subprocess.run(
                command_list,
                cwd=cwd,
                env=env,
                timeout=timeout,
                capture_output=capture_output,
                text=True,
                check=False  # Don't raise exception on non-zero exit
            )

            if result.returncode != 0:
                error_msg = f"Command failed with exit code {result.returncode}"
                if result.stderr:
                    error_msg += f": {result.stderr}"
                raise subprocess.CalledProcessError(
                    result.returncode, command_list, result.stdout, result.stderr
                )

            return result

        except subprocess.TimeoutExpired as e:
            raise TimeoutError(f"Command timed out after {timeout} seconds: {' '.join(command_list)}")

    def check_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        try:
            result = subprocess.run(
                ["docker", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def check_gpu_available(self) -> bool:
        """Check if GPU is available"""
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            # If torch is not available, try nvidia-smi
            try:
                result = subprocess.run(
                    ["nvidia-smi"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
            except (subprocess.TimeoutExpired, FileNotFoundError):
                return False

    def get_framework_info(self) -> Dict[str, Any]:
        """Get information about this framework adapter"""
        return {
            "name": self.framework_name,
            "class": self.__class__.__name__,
            "config": self.config.dict(),
            "prerequisites": self.validate_prerequisites(),
            "docker_available": self.check_docker_available(),
            "gpu_available": self.check_gpu_available(),
        }

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(framework={self.framework_name})"

    def __repr__(self) -> str:
        return self.__str__()


class ScriptBasedAdapter(BaseEvaluationAdapter):
    """
    Base class for adapters that execute shell scripts

    This class provides common functionality for frameworks that are
    implemented as shell scripts (like the existing evaluation scripts).
    """

    @abstractmethod
    def get_script_path(self) -> Path:
        """Get the path to the evaluation script"""
        pass

    @abstractmethod
    def build_command(self, context: ExecutionContext, **kwargs) -> List[str]:
        """Build the command line for script execution"""
        pass

    def validate_prerequisites(self) -> List[str]:
        """Default validation for script-based adapters"""
        errors = []

        # Check if script exists
        script_path = self.get_script_path()
        if not script_path.exists():
            errors.append(f"Script not found: {script_path}")
        elif not script_path.is_file():
            errors.append(f"Script path is not a file: {script_path}")

        # Check if script is executable
        if script_path.exists() and not script_path.stat().st_mode & 0o111:
            errors.append(f"Script is not executable: {script_path}")

        return errors

    def execute_evaluation(
        self,
        context: ExecutionContext,
        prepared_params: Dict[str, Any],
        **kwargs
    ) -> EvaluationResult:
        """Default execution for script-based adapters"""
        result = EvaluationResult(
            run_id=context.run_id,
            framework=self.framework_name,
            model=kwargs.get("model", "unknown"),
            start_time=datetime.now(),
            status="running"
        )

        try:
            # Build command
            command = self.build_command(context, **prepared_params, **kwargs)

            # Execute command
            with open(context.log_file, "w") as log_file:
                process_result = subprocess.run(
                    command,
                    cwd=self.get_script_path().parent,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=self.config.timeout
                )

            if process_result.returncode != 0:
                raise subprocess.CalledProcessError(
                    process_result.returncode,
                    command,
                    None,
                    f"Script execution failed with exit code {process_result.returncode}"
                )

            result.status = "success"

        except subprocess.TimeoutExpired:
            result.status = "error"
            result.error_message = f"Evaluation timed out after {self.config.timeout} seconds"

        except subprocess.CalledProcessError as e:
            result.status = "error"
            result.error_message = f"Script execution failed: {e}"

        return result
