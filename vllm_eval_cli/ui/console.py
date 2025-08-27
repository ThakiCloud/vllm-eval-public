"""
Console utilities for VLLM Evaluation CLI

This module provides Rich-based console utilities for enhanced terminal output including:
- Colored and styled text output
- Progress indicators
- Tables and panels
- Interactive prompts
- Status displays
"""

import sys
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# Custom theme for VLLM Eval CLI
VLLM_THEME = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "red bold",
    "success": "green bold",
    "highlight": "magenta",
    "dim": "bright_black",
    "progress": "blue",
    "title": "bold blue",
    "subtitle": "bold",
    "framework": "bright_green",
    "model": "bright_yellow",
    "metric": "bright_cyan",
})


def create_console(
    stderr: bool = False,
    force_terminal: Optional[bool] = None,
    width: Optional[int] = None,
) -> Console:
    """Create a configured Rich console instance"""
    return Console(
        theme=VLLM_THEME,
        stderr=stderr,
        force_terminal=force_terminal,
        width=width,
        highlight=False,  # Disable automatic highlighting
    )


def create_progress() -> Progress:
    """Create a configured progress bar for evaluations"""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        MofNCompleteColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        TextColumn("•"),
        TimeRemainingColumn(),
        refresh_per_second=4,
        console=create_console(),
    )


def print_header(title: str, subtitle: Optional[str] = None) -> None:
    """Print a styled header"""
    console = create_console()

    header_text = f"🚀 {title}"
    if subtitle:
        header_text += f"\n{subtitle}"

    panel = Panel(
        header_text,
        style="title",
        border_style="blue",
        padding=(1, 2),
    )

    console.print(panel)
    console.print()


def print_section(title: str, content: Optional[str] = None) -> None:
    """Print a section header with optional content"""
    console = create_console()

    # Print section title
    console.print(f"[subtitle]📋 {title}[/subtitle]")

    if content:
        console.print(f"[dim]{content}[/dim]")

    console.print()


def print_success(message: str) -> None:
    """Print a success message"""
    console = create_console()
    console.print(f"[success]✅ {message}[/success]")


def print_warning(message: str) -> None:
    """Print a warning message"""
    console = create_console()
    console.print(f"[warning]⚠️  {message}[/warning]")


def print_error(message: str) -> None:
    """Print an error message"""
    console = create_console()
    console.print(f"[error]❌ {message}[/error]")


def print_info(message: str) -> None:
    """Print an info message"""
    console = create_console()
    console.print(f"[info]ℹ️  {message}[/info]")


def print_framework_status(framework: str, status: str, details: Optional[str] = None) -> None:
    """Print framework status with appropriate styling"""
    console = create_console()

    # Status emoji mapping
    status_emojis = {
        "ready": "🟢",
        "running": "🔄",
        "success": "✅",
        "error": "❌",
        "warning": "🟡",
        "loading": "⏳",
        "disabled": "⚫",
    }

    emoji = status_emojis.get(status.lower(), "❓")
    status_text = f"{emoji} [framework]{framework}[/framework]"

    if details:
        status_text += f" - [dim]{details}[/dim]"

    console.print(status_text)


def create_results_table(results: List[Dict[str, Any]]) -> Table:
    """Create a table for displaying evaluation results"""
    table = Table(
        title="📊 Evaluation Results",
        show_header=True,
        header_style="bold blue",
        border_style="blue",
    )

    # Add columns
    table.add_column("Framework", style="framework", width=15)
    table.add_column("Model", style="model", width=20)
    table.add_column("Benchmark", style="subtitle", width=15)
    table.add_column("Score", style="metric", justify="right", width=10)
    table.add_column("Status", justify="center", width=10)
    table.add_column("Duration", style="dim", justify="right", width=10)

    # Add rows
    for result in results:
        status_style = "success" if result.get("status") == "success" else "error"
        table.add_row(
            result.get("framework", "Unknown"),
            result.get("model", "Unknown"),
            result.get("benchmark", "Unknown"),
            f"{result.get('score', 0):.2f}%",
            f"[{status_style}]{result.get('status', 'Unknown')}[/{status_style}]",
            result.get("duration", "Unknown"),
        )

    return table


def create_config_table(config_data: Dict[str, Any]) -> Table:
    """Create a table for displaying configuration"""
    table = Table(
        title="⚙️ Configuration Summary",
        show_header=True,
        header_style="bold blue",
        border_style="blue",
    )

    table.add_column("Setting", style="subtitle", width=25)
    table.add_column("Value", style="info", width=40)
    table.add_column("Description", style="dim", width=35)

    # Flatten configuration data
    for key, value in config_data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                table.add_row(
                    f"{key}.{sub_key}",
                    str(sub_value),
                    f"Configuration for {key}"
                )
        else:
            table.add_row(
                key,
                str(value),
                f"Global {key} setting"
            )

    return table


def create_system_status_table(status_data: Dict[str, Any]) -> Table:
    """Create a table for displaying system status"""
    table = Table(
        title="🔧 System Status",
        show_header=True,
        header_style="bold blue",
        border_style="blue",
    )

    table.add_column("Component", style="subtitle", width=20)
    table.add_column("Status", justify="center", width=15)
    table.add_column("Details", style="dim", width=40)

    for component, data in status_data.items():
        status = data.get("status", "unknown")
        details = data.get("details", "No details available")

        # Style status based on value
        if status == "healthy":
            status_text = "[success]🟢 Healthy[/success]"
        elif status == "warning":
            status_text = "[warning]🟡 Warning[/warning]"
        elif status == "error":
            status_text = "[error]❌ Error[/error]"
        else:
            status_text = f"❓ {status.title()}"

        table.add_row(component.title(), status_text, details)

    return table


def prompt_yes_no(question: str, default: bool = True) -> bool:
    """Prompt user for yes/no confirmation"""
    console = create_console()

    default_text = "Y/n" if default else "y/N"
    prompt_text = f"[info]{question}[/info] [{default_text}]: "

    try:
        response = console.input(prompt_text).strip().lower()

        if not response:
            return default

        return response in ('y', 'yes', '1', 'true')

    except (KeyboardInterrupt, EOFError):
        console.print("\n[warning]Operation cancelled[/warning]")
        return False


def prompt_choice(
    question: str,
    choices: List[str],
    default: Optional[str] = None,
) -> Optional[str]:
    """Prompt user to choose from a list of options"""
    console = create_console()

    # Display question and choices
    console.print(f"[info]{question}[/info]")
    for i, choice in enumerate(choices, 1):
        marker = "→" if choice == default else " "
        console.print(f"  {marker} {i}. {choice}")

    if default:
        prompt_text = f"Choose (1-{len(choices)}) [default: {default}]: "
    else:
        prompt_text = f"Choose (1-{len(choices)}): "

    try:
        while True:
            response = console.input(prompt_text).strip()

            # Use default if no response
            if not response and default:
                return default

            # Try to parse as number
            try:
                choice_num = int(response)
                if 1 <= choice_num <= len(choices):
                    return choices[choice_num - 1]
                else:
                    console.print(f"[error]Please enter a number between 1 and {len(choices)}[/error]")
            except ValueError:
                # Try to match choice text
                for choice in choices:
                    if response.lower() == choice.lower():
                        return choice
                console.print("[error]Invalid choice. Please try again.[/error]")

    except (KeyboardInterrupt, EOFError):
        console.print("\n[warning]Operation cancelled[/warning]")
        return None


def prompt_input(
    question: str,
    default: Optional[str] = None,
    required: bool = False,
    validator: Optional[callable] = None,
) -> Optional[str]:
    """Prompt user for text input with validation"""
    console = create_console()

    if default:
        prompt_text = f"[info]{question}[/info] [default: {default}]: "
    else:
        prompt_text = f"[info]{question}[/info]: "

    try:
        while True:
            response = console.input(prompt_text).strip()

            # Use default if no response
            if not response and default:
                response = default

            # Check if required
            if required and not response:
                console.print("[error]This field is required[/error]")
                continue

            # Run validator if provided
            if validator and response:
                try:
                    if not validator(response):
                        console.print("[error]Invalid input. Please try again.[/error]")
                        continue
                except Exception as e:
                    console.print(f"[error]Validation error: {e}[/error]")
                    continue

            return response if response else None

    except (KeyboardInterrupt, EOFError):
        console.print("\n[warning]Operation cancelled[/warning]")
        return None


def display_evaluation_progress(
    framework: str,
    model: str,
    current_task: str,
    progress: float,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Display real-time evaluation progress"""
    console = create_console()

    # Clear screen and display header
    console.clear()
    print_header(f"Running {framework} Evaluation", f"Model: {model}")

    # Display current task
    console.print(f"[progress]📊 Current Task:[/progress] {current_task}")
    console.print(f"[progress]🔄 Progress:[/progress] {progress:.1f}%")
    console.print()

    # Display progress bar
    progress_bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
    console.print(f"[progress][{progress_bar}] {progress:.1f}%[/progress]")
    console.print()

    # Display additional details if provided
    if details:
        console.print("[subtitle]📈 Real-time Metrics:[/subtitle]")
        for key, value in details.items():
            console.print(f"├─ {key}: [metric]{value}[/metric]")
        console.print()

    console.print("[dim]💡 Tip: Press Ctrl+C to safely interrupt[/dim]")


# Export main console instance
console = create_console()
