"""
System Command Module

This module implements the 'system' command for system management, diagnostics,
and health checks of the VLLM evaluation environment.
"""

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import typer

from vllm_eval_cli.adapters import get_available_adapters, validate_all_adapters
from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import (
    console,
    create_system_status_table,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    prompt_yes_no,
)

# Create system command app
app = typer.Typer(
    name="system",
    help="🔧 System management and diagnostics",
    rich_markup_mode="rich",
)


@app.command()
def status(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed status"),
) -> None:
    """📊 Show system status"""
    print_header("System Status")

    config_manager = ctx.obj["config_manager"]

    # Collect system status information
    status_data = {}

    # Check Python environment
    status_data["python"] = check_python_environment()

    # Check Docker
    status_data["docker"] = check_docker_status()

    # Check GPU
    status_data["gpu"] = check_gpu_status()

    # Check disk space
    status_data["disk_space"] = check_disk_space(config_manager)

    # Check evaluation frameworks
    framework_status = check_frameworks_status(config_manager)
    status_data.update(framework_status)

    # Display status table
    table = create_system_status_table(status_data)
    console.print(table)

    # Show detailed information if verbose
    if verbose:
        show_detailed_status(status_data)


@app.command()
def doctor(
    ctx: typer.Context,
    fix: bool = typer.Option(False, "--fix", help="Attempt to fix issues automatically"),
) -> None:
    """🩺 Diagnose and fix system issues"""
    print_header("System Diagnostics")

    config_manager = ctx.obj["config_manager"]
    issues_found = []

    print_info("Running comprehensive system diagnostics...")

    # Check configuration
    print_info("🔍 Checking configuration...")
    config_issues = config_manager.validate_config()
    if config_issues:
        issues_found.extend([f"Config: {issue}" for issue in config_issues])
    else:
        print_success("Configuration is valid")

    # Check dependencies
    print_info("🔍 Checking dependencies...")
    dependency_issues = check_dependencies()
    if dependency_issues:
        issues_found.extend([f"Dependency: {issue}" for issue in dependency_issues])
    else:
        print_success("All dependencies are available")

    # Check frameworks
    print_info("🔍 Checking evaluation frameworks...")
    framework_validation = validate_all_adapters(config_manager)
    for framework, errors in framework_validation.items():
        if errors:
            issues_found.extend([f"{framework}: {error}" for error in errors])

    if not any(framework_validation.values()):
        print_success("All frameworks are ready")

    # Check file permissions
    print_info("🔍 Checking file permissions...")
    permission_issues = check_file_permissions(config_manager)
    if permission_issues:
        issues_found.extend([f"Permission: {issue}" for issue in permission_issues])
    else:
        print_success("File permissions are correct")

    # Show results
    console.print()
    if not issues_found:
        print_success("🎉 No issues found! System is healthy.")
        return

    print_warning(f"Found {len(issues_found)} issues:")
    for i, issue in enumerate(issues_found, 1):
        print_error(f"{i}. {issue}")

    if fix:
        console.print()
        print_info("🔧 Attempting to fix issues...")
        fixed_count = attempt_fixes(config_manager, issues_found)
        print_info(f"Fixed {fixed_count} out of {len(issues_found)} issues")
    else:
        console.print()
        print_info("💡 Run with --fix to attempt automatic fixes")


@app.command()
def clean(
    ctx: typer.Context,
    cache: bool = typer.Option(True, "--cache/--no-cache", help="Clean cache directories"),
    logs: bool = typer.Option(True, "--logs/--no-logs", help="Clean old log files"),
    temp: bool = typer.Option(True, "--temp/--no-temp", help="Clean temporary files"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """🧹 Clean up temporary files and caches"""
    print_header("System Cleanup")

    config_manager = ctx.obj["config_manager"]

    cleanup_items = []
    if cache:
        cleanup_items.append("Cache directories")
    if logs:
        cleanup_items.append("Old log files")
    if temp:
        cleanup_items.append("Temporary files")

    if not cleanup_items:
        print_warning("Nothing to clean (all options disabled)")
        return

    print_info(f"Will clean: {', '.join(cleanup_items)}")

    if not force:
        if not prompt_yes_no("Continue with cleanup?", default=True):
            print_info("Cleanup cancelled")
            return

    cleaned_size = 0

    # Clean cache directories
    if cache:
        cache_size = clean_cache_directories(config_manager)
        cleaned_size += cache_size
        print_success(f"Cleaned cache directories ({format_size(cache_size)})")

    # Clean old logs
    if logs:
        log_size = clean_old_logs(config_manager)
        cleaned_size += log_size
        print_success(f"Cleaned old log files ({format_size(log_size)})")

    # Clean temporary files
    if temp:
        temp_size = clean_temp_files(config_manager)
        cleaned_size += temp_size
        print_success(f"Cleaned temporary files ({format_size(temp_size)})")

    console.print()
    print_success(f"🎉 Cleanup completed! Freed {format_size(cleaned_size)} of disk space")


@app.command()
def logs(
    ctx: typer.Context,
    lines: int = typer.Option(50, "--lines", "-n", help="Number of lines to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow log output"),
    component: Optional[str] = typer.Option(None, "--component", "-c", help="Show logs for specific component"),
) -> None:
    """📜 Show system logs"""
    config_manager = ctx.obj["config_manager"]

    logs_dir = config_manager.config.system.logs_dir

    if component:
        print_header(f"Logs for {component}")
        log_file = logs_dir / f"{component}.log"
    else:
        print_header("System Logs")
        # Find the most recent log file
        log_files = list(logs_dir.glob("*.log"))
        if not log_files:
            print_warning("No log files found")
            return
        log_file = max(log_files, key=lambda f: f.stat().st_mtime)

    if not log_file.exists():
        print_error(f"Log file not found: {log_file}")
        return

    try:
        if follow:
            # Use tail -f equivalent
            subprocess.run(["tail", "-f", "-n", str(lines), str(log_file)])
        else:
            # Read last N lines
            with open(log_file, "r") as f:
                all_lines = f.readlines()
                recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

                for line in recent_lines:
                    console.print(line.rstrip())

    except KeyboardInterrupt:
        print_info("\nLog viewing stopped")
    except Exception as e:
        print_error(f"Failed to read log file: {e}")


def check_python_environment() -> Dict[str, Any]:
    """Check Python environment status"""
    try:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return {
            "status": "healthy",
            "details": f"Python {python_version}",
        }
    except Exception as e:
        return {
            "status": "error",
            "details": f"Python check failed: {e}",
        }


def check_docker_status() -> Dict[str, Any]:
    """Check Docker availability and status"""
    try:
        result = subprocess.run(
            ["docker", "version", "--format", "{{.Server.Version}}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return {
                "status": "healthy",
                "details": f"Docker {version}",
            }
        else:
            return {
                "status": "error",
                "details": "Docker daemon not running",
            }
    except FileNotFoundError:
        return {
            "status": "error",
            "details": "Docker not installed",
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "warning",
            "details": "Docker check timed out",
        }


def check_gpu_status() -> Dict[str, Any]:
    """Check GPU availability"""
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0) if gpu_count > 0 else "Unknown"
            return {
                "status": "healthy",
                "details": f"{gpu_count} GPU(s): {gpu_name}",
            }
        else:
            return {
                "status": "warning",
                "details": "CUDA not available",
            }
    except ImportError:
        # Fallback to nvidia-smi
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=count,name", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return {
                    "status": "healthy",
                    "details": "GPU detected via nvidia-smi",
                }
            else:
                return {
                    "status": "warning",
                    "details": "No GPU detected",
                }
        except FileNotFoundError:
            return {
                "status": "warning",
                "details": "No GPU tools available",
            }


def check_disk_space(config_manager: ConfigManager) -> Dict[str, Any]:
    """Check disk space in key directories"""
    try:
        results_dir = config_manager.config.system.results_dir
        cache_dir = config_manager.config.system.cache_dir

        # Check available space
        results_usage = shutil.disk_usage(results_dir.parent)
        free_gb = results_usage.free / (1024**3)

        if free_gb < 1:
            status = "error"
            details = f"Low disk space: {free_gb:.1f}GB free"
        elif free_gb < 5:
            status = "warning"
            details = f"Limited disk space: {free_gb:.1f}GB free"
        else:
            status = "healthy"
            details = f"Disk space OK: {free_gb:.1f}GB free"

        return {
            "status": status,
            "details": details,
        }
    except Exception as e:
        return {
            "status": "error",
            "details": f"Disk check failed: {e}",
        }


def check_frameworks_status(config_manager: ConfigManager) -> Dict[str, Dict[str, Any]]:
    """Check status of all evaluation frameworks"""
    frameworks_status = {}
    validation_results = validate_all_adapters(config_manager)

    for framework, errors in validation_results.items():
        if not errors:
            frameworks_status[f"framework_{framework}"] = {
                "status": "healthy",
                "details": "Ready to use",
            }
        else:
            frameworks_status[f"framework_{framework}"] = {
                "status": "error",
                "details": f"{len(errors)} issues found",
            }

    return frameworks_status


def check_dependencies() -> list:
    """Check if required dependencies are available"""
    issues = []

    required_packages = [
        "typer",
        "rich",
        "pydantic",
        "toml",
    ]

    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            issues.append(f"Missing required package: {package}")

    return issues


def check_file_permissions(config_manager: ConfigManager) -> list:
    """Check file and directory permissions"""
    issues = []

    directories_to_check = [
        config_manager.config.system.results_dir,
        config_manager.config.system.logs_dir,
        config_manager.config.system.cache_dir,
    ]

    for directory in directories_to_check:
        try:
            directory.mkdir(parents=True, exist_ok=True)

            # Test write permissions
            test_file = directory / ".permission_test"
            test_file.write_text("test")
            test_file.unlink()

        except PermissionError:
            issues.append(f"No write permission for {directory}")
        except Exception as e:
            issues.append(f"Permission check failed for {directory}: {e}")

    return issues


def show_detailed_status(status_data: Dict[str, Dict[str, Any]]) -> None:
    """Show detailed status information"""
    console.print("\n[bold]Detailed Status Information:[/bold]")

    for component, data in status_data.items():
        status = data.get("status", "unknown")
        details = data.get("details", "No details available")

        if status == "healthy":
            console.print(f"✅ {component}: {details}")
        elif status == "warning":
            console.print(f"⚠️  {component}: {details}")
        elif status == "error":
            console.print(f"❌ {component}: {details}")
        else:
            console.print(f"❓ {component}: {details}")


def attempt_fixes(config_manager: ConfigManager, issues: list) -> int:
    """Attempt to automatically fix common issues"""
    fixed_count = 0

    for issue in issues:
        if "Permission" in issue and "write permission" in issue:
            # Try to fix permission issues
            try:
                # Create directories with proper permissions
                for directory in [
                    config_manager.config.system.results_dir,
                    config_manager.config.system.logs_dir,
                    config_manager.config.system.cache_dir,
                ]:
                    directory.mkdir(parents=True, exist_ok=True, mode=0o755)
                fixed_count += 1
                print_success(f"Fixed permission issue for {directory}")
            except Exception as e:
                print_error(f"Failed to fix permission issue: {e}")

    return fixed_count


def clean_cache_directories(config_manager: ConfigManager) -> int:
    """Clean cache directories and return bytes cleaned"""
    cache_dir = config_manager.config.system.cache_dir
    cleaned_size = 0

    if cache_dir.exists():
        for item in cache_dir.rglob("*"):
            if item.is_file():
                try:
                    size = item.stat().st_size
                    item.unlink()
                    cleaned_size += size
                except Exception:
                    pass

    return cleaned_size


def clean_old_logs(config_manager: ConfigManager) -> int:
    """Clean old log files and return bytes cleaned"""
    logs_dir = config_manager.config.system.logs_dir
    max_log_files = config_manager.config.system.max_log_files
    cleaned_size = 0

    if logs_dir.exists():
        log_files = sorted(
            logs_dir.glob("*.log"),
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )

        # Keep only the most recent log files
        for log_file in log_files[max_log_files:]:
            try:
                size = log_file.stat().st_size
                log_file.unlink()
                cleaned_size += size
            except Exception:
                pass

    return cleaned_size


def clean_temp_files(config_manager: ConfigManager) -> int:
    """Clean temporary files and return bytes cleaned"""
    temp_dir = config_manager.config.system.temp_dir
    cleaned_size = 0

    if temp_dir.exists():
        for item in temp_dir.rglob("*"):
            if item.is_file():
                try:
                    size = item.stat().st_size
                    item.unlink()
                    cleaned_size += size
                except Exception:
                    pass

    return cleaned_size


def format_size(bytes_size: int) -> str:
    """Format bytes as human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024
    return f"{bytes_size:.1f} TB"


@app.callback()
def system_callback() -> None:
    """🔧 System management, diagnostics, and maintenance tools"""
    pass
