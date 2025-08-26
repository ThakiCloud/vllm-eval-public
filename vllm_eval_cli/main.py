#!/usr/bin/env python3
"""
Main CLI application for VLLM Evaluation System

This module provides the primary entry point for the vllm-eval CLI tool,
implementing a Typer-based command interface with rich terminal output.
"""

from vllm_eval_cli.commands import batch, config, results, run, setup, system
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.traceback import install

from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import create_console

# Install rich traceback handler for better error displays
install(show_locals=True)

# Create global console instance
console = create_console()

# Create main Typer application
app = typer.Typer(
    name="vllm-eval",
    help="🚀 VLLM Evaluation CLI - Unified interface for model evaluation systems",
    add_completion=True,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    profile: Optional[str] = typer.Option(
        None,
        "--profile",
        "-p",
        help="Configuration profile to use",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose output",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode",
    ),
) -> None:
    """
    🚀 VLLM Evaluation CLI

    Unified command-line interface for running model evaluations across multiple frameworks:
    • Evalchemy benchmarks
    • NVIDIA Eval suite
    • VLLM performance benchmarks
    • Deepeval testing

    Use 'vllm-eval COMMAND --help' for detailed help on specific commands.
    """
    # Store global options in context
    ctx.ensure_object(dict)
    ctx.obj["config_file"] = config_file
    ctx.obj["profile"] = profile
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug

    # Initialize configuration manager
    try:
        config_manager = ConfigManager(config_file=config_file, profile=profile)
        ctx.obj["config_manager"] = config_manager
    except Exception as e:
        if debug:
            console.print_exception()
        else:
            console.print(f"[red]❌ Configuration error: {e}[/red]")
        raise typer.Exit(1)


# Import and register command modules


# Register command groups
app.add_typer(run.app, name="run", help="🏃 Execute evaluation frameworks")
app.add_typer(config.app, name="config", help="⚙️  Manage configuration profiles")
app.add_typer(system.app, name="system", help="🔧 System management and diagnostics")
app.add_typer(results.app, name="results", help="📊 Manage evaluation results")
app.add_typer(batch.app, name="batch", help="📦 Batch processing operations")


@app.command()
def setup(
    interactive: bool = typer.Option(
        True, "--interactive/--no-interactive", help="Run interactive setup wizard"
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite existing configuration"),
) -> None:
    """🎯 Setup wizard for VLLM Evaluation CLI"""
    from vllm_eval_cli.commands.setup import setup_wizard

    setup_wizard(interactive=interactive, force=force)


@app.command()
def version() -> None:
    """📋 Show version information"""
    from vllm_eval_cli import __version__, __title__, __description__

    console.print(f"[bold green]{__title__}[/bold green] version [bold]{__version__}[/bold]")
    console.print(f"[dim]{__description__}[/dim]")


@app.command()
def doctor() -> None:
    """🩺 Diagnose system and configuration issues"""
    from vllm_eval_cli.commands.system import run_doctor

    run_doctor()


def cli() -> None:
    """Entry point for the CLI application"""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Operation cancelled by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]❌ Unexpected error: {e}[/red]")
        console.print("\n[dim]Use --debug flag for detailed error information[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
