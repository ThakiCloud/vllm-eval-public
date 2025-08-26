"""
Run Command Module

This module implements the 'run' command for executing various evaluation frameworks
through the unified CLI interface. It supports running individual frameworks or
all enabled frameworks in sequence or parallel.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.progress import Progress, SpinnerColumn, TextColumn

from vllm_eval_cli.adapters import create_adapter, get_available_adapters
from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import (
    console,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
)

# Create run command app
app = typer.Typer(
    name="run",
    help="🏃 Execute evaluation frameworks",
    rich_markup_mode="rich",
)


@app.command()
def evalchemy(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="API endpoint URL"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", "-b", help="Batch size"),
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help="Custom run ID"),
    config_name: Optional[str] = typer.Option(None, "--config", "-c", help="Evalchemy config name"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """🧪 Run Evalchemy benchmark evaluation"""
    print_header("Evalchemy Evaluation", f"Model: {model}")

    config_manager = ctx.obj["config_manager"]

    try:
        # Create adapter with overrides
        adapter_kwargs = {}
        if endpoint:
            adapter_kwargs["endpoint"] = endpoint
        if batch_size:
            adapter_kwargs["batch_size"] = batch_size

        adapter = create_adapter("evalchemy", config_manager, **adapter_kwargs)

        # Run evaluation
        result = adapter.run_evaluation(
            model=model,
            output_dir=output,
            run_id=run_id,
            dry_run=dry_run,
            verbose=verbose,
            config_name=config_name,
        )

        # Display results
        if result.status == "success":
            print_success(f"Evalchemy evaluation completed successfully!")
            if result.overall_score is not None:
                print_info(f"Overall Score: {result.overall_score:.2f}%")
        elif result.status == "dry_run":
            print_info("Dry run completed - no actual execution performed")
        else:
            print_error(f"Evaluation failed: {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Evalchemy evaluation failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def standard_evalchemy(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="API endpoint URL"),
    batch_size: Optional[int] = typer.Option(None, "--batch-size", "-b", help="Batch size"),
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help="Custom run ID"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """📊 Run Standard Evalchemy evaluation"""
    print_header("Standard Evalchemy Evaluation", f"Model: {model}")

    config_manager = ctx.obj["config_manager"]

    try:
        # Create adapter with overrides
        adapter_kwargs = {}
        if endpoint:
            adapter_kwargs["endpoint"] = endpoint
        if batch_size:
            adapter_kwargs["batch_size"] = batch_size

        adapter = create_adapter("standard_evalchemy", config_manager, **adapter_kwargs)

        # Run evaluation
        result = adapter.run_evaluation(
            model=model,
            output_dir=output,
            run_id=run_id,
            dry_run=dry_run,
            verbose=verbose,
        )

        # Display results
        if result.status == "success":
            print_success(f"Standard Evalchemy evaluation completed successfully!")
            if result.overall_score is not None:
                print_info(f"Overall Score: {result.overall_score:.2f}%")
        elif result.status == "dry_run":
            print_info("Dry run completed - no actual execution performed")
        else:
            print_error(f"Evaluation failed: {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Standard Evalchemy evaluation failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def nvidia(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    benchmark: str = typer.Option("livecodebench", "--benchmark", "-b", help="Benchmark to run"),
    model_path: Optional[str] = typer.Option(None, "--model-path", "-m", help="Path to model"),
    gpus: Optional[int] = typer.Option(None, "--gpus", "-g", help="Number of GPUs"),
    out_seq_len: Optional[int] = typer.Option(None, "--out-seq-len", help="Output sequence length"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """🚀 Run NVIDIA evaluation suite"""
    print_header("NVIDIA Evaluation", f"Model: {model} | Benchmark: {benchmark}")

    config_manager = ctx.obj["config_manager"]

    try:
        # Create adapter with overrides
        adapter_kwargs = {"benchmark": benchmark}
        if model_path:
            adapter_kwargs["model_path"] = model_path
        if gpus:
            adapter_kwargs["gpu_count"] = gpus
        if out_seq_len:
            adapter_kwargs["out_seq_len"] = out_seq_len

        adapter = create_adapter("nvidia", config_manager, **adapter_kwargs)

        # Run evaluation
        result = adapter.run_evaluation(
            model=model,
            output_dir=output,
            dry_run=dry_run,
            verbose=verbose,
            model_path=model_path,
        )

        # Display results
        if result.status == "success":
            print_success(f"NVIDIA {benchmark} evaluation completed successfully!")
            if result.overall_score is not None:
                print_info(f"Overall Score: {result.overall_score:.2f}%")
        elif result.status == "dry_run":
            print_info("Dry run completed - no actual execution performed")
        else:
            print_error(f"Evaluation failed: {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"NVIDIA evaluation failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def vllm_benchmark(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    scenario: str = typer.Option("performance", "--scenario", "-s", help="Benchmark scenario"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="API endpoint URL"),
    concurrency: Optional[int] = typer.Option(None, "--concurrency", "-c", help="Concurrency level"),
    duration: Optional[int] = typer.Option(None, "--duration", "-d", help="Test duration (seconds)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """⚡ Run VLLM performance benchmark"""
    print_header("VLLM Benchmark", f"Model: {model} | Scenario: {scenario}")

    config_manager = ctx.obj["config_manager"]

    try:
        # Create adapter with overrides
        adapter_kwargs = {"scenario": scenario}
        if endpoint:
            adapter_kwargs["endpoint"] = endpoint
        if concurrency:
            adapter_kwargs["concurrency"] = concurrency
        if duration:
            adapter_kwargs["duration"] = duration

        adapter = create_adapter("vllm_benchmark", config_manager, **adapter_kwargs)

        # Run evaluation
        result = adapter.run_evaluation(
            model=model,
            output_dir=output,
            dry_run=dry_run,
            verbose=verbose,
        )

        # Display results
        if result.status == "success":
            print_success(f"VLLM {scenario} benchmark completed successfully!")
            if result.overall_score is not None:
                print_info(f"Overall Score: {result.overall_score:.2f}")
        elif result.status == "dry_run":
            print_info("Dry run completed - no actual execution performed")
        else:
            print_error(f"Benchmark failed: {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"VLLM benchmark failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def deepeval(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    test_suite: str = typer.Option("default", "--suite", "-s", help="Test suite to run"),
    metrics: Optional[str] = typer.Option(None, "--metrics", "-m", help="Comma-separated metrics"),
    endpoint: Optional[str] = typer.Option(None, "--endpoint", "-e", help="API endpoint URL"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """🧪 Run Deepeval testing framework"""
    print_header("Deepeval Testing", f"Model: {model} | Suite: {test_suite}")

    config_manager = ctx.obj["config_manager"]

    try:
        # Create adapter with overrides
        adapter_kwargs = {"test_suite": test_suite}
        if endpoint:
            adapter_kwargs["endpoint"] = endpoint
        if metrics:
            adapter_kwargs["metrics"] = [m.strip() for m in metrics.split(",")]

        adapter = create_adapter("deepeval", config_manager, **adapter_kwargs)

        # Run evaluation
        result = adapter.run_evaluation(
            model=model,
            output_dir=output,
            dry_run=dry_run,
            verbose=verbose,
        )

        # Display results
        if result.status in ["success", "partial_success"]:
            print_success(f"Deepeval {test_suite} testing completed!")
            if result.overall_score is not None:
                print_info(f"Overall Score: {result.overall_score:.2f}%")
        elif result.status == "dry_run":
            print_info("Dry run completed - no actual execution performed")
        else:
            print_error(f"Testing failed: {result.error_message}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Deepeval testing failed: {e}")
        if verbose:
            console.print_exception()
        raise typer.Exit(1)


@app.command()
def all(
    ctx: typer.Context,
    model: str = typer.Argument(..., help="Model name or identifier"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output directory"),
    parallel: bool = typer.Option(False, "--parallel", "-p", help="Run frameworks in parallel"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be executed"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """🚀 Run all enabled evaluation frameworks"""
    print_header("All Frameworks Evaluation", f"Model: {model}")

    config_manager = ctx.obj["config_manager"]

    # Get enabled frameworks
    enabled_frameworks = []
    available_frameworks = get_available_adapters()

    for framework in available_frameworks.keys():
        try:
            framework_config = config_manager.get_framework_config(framework)
            if framework_config.enabled:
                enabled_frameworks.append(framework)
        except Exception:
            continue

    if not enabled_frameworks:
        print_warning("No frameworks are enabled in configuration")
        raise typer.Exit(1)

    print_info(f"Running {len(enabled_frameworks)} enabled frameworks: {', '.join(enabled_frameworks)}")

    results = {}

    if parallel:
        print_info("Running frameworks in parallel (not yet implemented)")
        # TODO: Implement parallel execution
        print_warning("Parallel execution not yet implemented, falling back to sequential")

    # Sequential execution
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:

        for framework in enabled_frameworks:
            task = progress.add_task(f"Running {framework}...", total=None)

            try:
                adapter = create_adapter(framework, config_manager)
                result = adapter.run_evaluation(
                    model=model,
                    output_dir=output / framework if output else None,
                    dry_run=dry_run,
                    verbose=verbose,
                )
                results[framework] = result

                if result.status == "success":
                    progress.update(task, description=f"✅ {framework} completed")
                else:
                    progress.update(task, description=f"❌ {framework} failed")

            except Exception as e:
                results[framework] = None
                progress.update(task, description=f"❌ {framework} error")
                if verbose:
                    print_error(f"{framework} failed: {e}")

            progress.remove_task(task)

    # Display summary
    console.print()
    print_header("Evaluation Summary")

    successful = 0
    failed = 0

    for framework, result in results.items():
        if result and result.status == "success":
            successful += 1
            score_text = f" ({result.overall_score:.2f}%)" if result.overall_score else ""
            print_success(f"{framework}: Completed{score_text}")
        else:
            failed += 1
            error_text = f" - {result.error_message}" if result and result.error_message else ""
            print_error(f"{framework}: Failed{error_text}")

    console.print()
    print_info(f"Summary: {successful} successful, {failed} failed out of {len(enabled_frameworks)} frameworks")

    if failed > 0:
        raise typer.Exit(1)


@app.callback()
def run_callback() -> None:
    """🏃 Execute evaluation frameworks with the unified CLI interface"""
    pass
