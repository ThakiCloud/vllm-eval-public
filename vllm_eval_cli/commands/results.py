"""
Results Command Module

This module implements the 'results' command for managing evaluation results,
including listing, viewing, comparing, and exporting results.
"""

import json
from pathlib import Path
from typing import Optional

import typer

from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import (
    console,
    create_results_table,
    print_error,
    print_header,
    print_info,
    print_success,
)

# Create results command app
app = typer.Typer(
    name="results",
    help="📊 Manage evaluation results",
    rich_markup_mode="rich",
)


@app.command()
def list(
    ctx: typer.Context,
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum number of results to show"),
) -> None:
    """📋 List evaluation results"""
    config_manager = ctx.obj["config_manager"]
    results_dir = config_manager.config.system.results_dir

    print_header("Evaluation Results")

    if not results_dir.exists():
        print_info("No results directory found")
        return

    # Find all result files
    result_files = list(results_dir.glob("**/result.json"))

    if not result_files:
        print_info("No evaluation results found")
        return

    # Parse and sort results
    results = []
    for result_file in result_files:
        try:
            with open(result_file, "r") as f:
                data = json.load(f)
            results.append(data)
        except Exception:
            continue

    # Sort by start time (newest first)
    results.sort(key=lambda x: x.get("start_time", ""), reverse=True)

    # Limit results
    results = results[:limit]

    # Display results table
    if results:
        table = create_results_table(results)
        console.print(table)
        print_info(f"Showing {len(results)} results (use --limit to show more)")
    else:
        print_info("No valid results found")


@app.command()
def show(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID to show"),
) -> None:
    """🔍 Show detailed evaluation result"""
    config_manager = ctx.obj["config_manager"]
    results_dir = config_manager.config.system.results_dir

    print_header(f"Evaluation Result: {run_id}")

    # Find result file
    result_file = results_dir / run_id / "result.json"
    if not result_file.exists():
        # Try to find in subdirectories
        result_files = list(results_dir.glob(f"**/{run_id}/result.json"))
        if result_files:
            result_file = result_files[0]
        else:
            print_error(f"Result not found: {run_id}")
            raise typer.Exit(1)

    try:
        with open(result_file, "r") as f:
            result_data = json.load(f)

        # Display basic information
        print_info(f"Framework: {result_data.get('framework', 'Unknown')}")
        print_info(f"Model: {result_data.get('model', 'Unknown')}")
        print_info(f"Status: {result_data.get('status', 'Unknown')}")
        print_info(f"Start Time: {result_data.get('start_time', 'Unknown')}")
        print_info(f"Duration: {result_data.get('duration_seconds', 'Unknown')} seconds")

        if result_data.get("overall_score"):
            print_success(f"Overall Score: {result_data['overall_score']:.2f}%")

        # Display detailed scores
        detailed_scores = result_data.get("detailed_scores", {})
        if detailed_scores:
            console.print("\n[bold]Detailed Scores:[/bold]")
            for metric, score in detailed_scores.items():
                console.print(f"  • {metric}: {score}")

        # Display metadata
        metadata = result_data.get("metadata", {})
        if metadata:
            console.print("\n[bold]Metadata:[/bold]")
            for key, value in metadata.items():
                console.print(f"  • {key}: {value}")

        # Display output files
        output_files = result_data.get("output_files", [])
        if output_files:
            console.print("\n[bold]Output Files:[/bold]")
            for file_path in output_files:
                console.print(f"  • {file_path}")

    except Exception as e:
        print_error(f"Failed to load result: {e}")
        raise typer.Exit(1)


@app.command()
def export(
    ctx: typer.Context,
    run_id: str = typer.Argument(..., help="Run ID to export"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file"),
) -> None:
    """💾 Export evaluation result"""
    print_info(f"Export functionality not yet implemented")
    # TODO: Implement result export


@app.callback()
def results_callback() -> None:
    """📊 Manage and analyze evaluation results"""
    pass
