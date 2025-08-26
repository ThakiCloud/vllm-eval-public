"""
Config Command Module

This module implements the 'config' command for managing configuration profiles,
viewing settings, and validating configurations.
"""

from pathlib import Path
from typing import Optional

import typer

from vllm_eval_cli.core.config import ConfigManager
from vllm_eval_cli.ui.console import (
    console,
    create_config_table,
    print_error,
    print_header,
    print_info,
    print_success,
    print_warning,
    prompt_input,
    prompt_yes_no,
    prompt_choice,
)

# Create config command app
app = typer.Typer(
    name="config",
    help="⚙️ Manage configuration profiles",
    rich_markup_mode="rich",
)


@app.command()
def show(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to show"),
    framework: Optional[str] = typer.Option(None, "--framework", "-f", help="Show specific framework config"),
) -> None:
    """📋 Show current configuration"""
    config_manager = ctx.obj["config_manager"]

    if profile and profile != config_manager.profile:
        # Create temporary config manager for the specified profile
        temp_config_manager = ConfigManager(profile=profile)
        config_data = temp_config_manager.get_config_summary()
        print_header(f"Configuration Profile: {profile}")
    else:
        config_data = config_manager.get_config_summary()
        print_header(f"Current Configuration Profile: {config_manager.profile}")

    if framework:
        # Show specific framework configuration
        try:
            if profile and profile != config_manager.profile:
                framework_config = temp_config_manager.get_framework_config(framework)
            else:
                framework_config = config_manager.get_framework_config(framework)

            print_info(f"Framework: {framework}")
            framework_data = {
                f"{framework}_{key}": value
                for key, value in framework_config.dict().items()
            }

            table = create_config_table(framework_data)
            console.print(table)
        except Exception as e:
            print_error(f"Failed to show {framework} configuration: {e}")
            raise typer.Exit(1)
    else:
        # Show all configuration
        table = create_config_table(config_data)
        console.print(table)


@app.command()
def list_profiles(
    ctx: typer.Context,
) -> None:
    """📝 List available configuration profiles"""
    config_manager = ctx.obj["config_manager"]

    print_header("Available Configuration Profiles")

    profiles = config_manager.list_profiles()

    if not profiles:
        print_warning("No configuration profiles found")
        print_info("Create a new profile with: vllm-eval config create <name>")
        return

    current_profile = config_manager.profile

    for profile in profiles:
        if profile == current_profile:
            print_success(f"• {profile} (current)")
        else:
            print_info(f"• {profile}")

    print_info(f"\nTotal: {len(profiles)} profiles")


@app.command()
def create(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Profile name"),
    base_profile: Optional[str] = typer.Option(None, "--base", "-b", help="Base profile to copy from"),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive setup"),
) -> None:
    """➕ Create a new configuration profile"""
    config_manager = ctx.obj["config_manager"]

    print_header(f"Creating Profile: {name}")

    try:
        # Check if profile already exists
        existing_profiles = config_manager.list_profiles()
        if name in existing_profiles:
            if not prompt_yes_no(f"Profile '{name}' already exists. Overwrite?", default=False):
                print_info("Profile creation cancelled")
                return

        # Create profile
        config_manager.create_profile(name, base_profile)
        print_success(f"Profile '{name}' created successfully")

        if interactive:
            # Ask if user wants to edit the new profile
            if prompt_yes_no("Do you want to edit the new profile now?", default=True):
                edit_profile_interactive(config_manager, name)

    except Exception as e:
        print_error(f"Failed to create profile: {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Profile name to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """🗑️ Delete a configuration profile"""
    config_manager = ctx.obj["config_manager"]

    print_header(f"Deleting Profile: {name}")

    try:
        # Check if profile exists
        existing_profiles = config_manager.list_profiles()
        if name not in existing_profiles:
            print_error(f"Profile '{name}' does not exist")
            raise typer.Exit(1)

        # Confirm deletion
        if not force:
            if not prompt_yes_no(f"Are you sure you want to delete profile '{name}'?", default=False):
                print_info("Profile deletion cancelled")
                return

        # Delete profile
        config_manager.delete_profile(name)
        print_success(f"Profile '{name}' deleted successfully")

    except Exception as e:
        print_error(f"Failed to delete profile: {e}")
        raise typer.Exit(1)


@app.command()
def edit(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to edit"),
    framework: Optional[str] = typer.Option(None, "--framework", "-f", help="Edit specific framework"),
) -> None:
    """✏️ Edit configuration profile interactively"""
    config_manager = ctx.obj["config_manager"]

    target_profile = profile or config_manager.profile
    print_header(f"Editing Profile: {target_profile}")

    try:
        if profile and profile != config_manager.profile:
            # Create temporary config manager for the specified profile
            edit_config_manager = ConfigManager(profile=profile)
        else:
            edit_config_manager = config_manager

        if framework:
            edit_framework_config(edit_config_manager, framework)
        else:
            edit_profile_interactive(edit_config_manager, target_profile)

    except Exception as e:
        print_error(f"Failed to edit configuration: {e}")
        raise typer.Exit(1)


@app.command()
def validate(
    ctx: typer.Context,
    profile: Optional[str] = typer.Option(None, "--profile", "-p", help="Profile to validate"),
) -> None:
    """✅ Validate configuration"""
    config_manager = ctx.obj["config_manager"]

    if profile and profile != config_manager.profile:
        # Create temporary config manager for the specified profile
        temp_config_manager = ConfigManager(profile=profile)
        target_profile = profile
    else:
        temp_config_manager = config_manager
        target_profile = config_manager.profile

    print_header(f"Validating Profile: {target_profile}")

    try:
        issues = temp_config_manager.validate_config()

        if not issues:
            print_success("Configuration is valid!")
        else:
            print_warning(f"Found {len(issues)} validation issues:")
            for i, issue in enumerate(issues, 1):
                print_error(f"{i}. {issue}")
            raise typer.Exit(1)

    except Exception as e:
        print_error(f"Validation failed: {e}")
        raise typer.Exit(1)


def edit_profile_interactive(config_manager: ConfigManager, profile_name: str) -> None:
    """Interactive profile editing"""
    print_info(f"Interactive editing for profile: {profile_name}")

    sections = [
        "Global Settings",
        "Framework Settings",
        "System Settings",
        "Save and Exit",
    ]

    while True:
        print_info("\nWhat would you like to edit?")
        choice = prompt_choice("Select section:", sections, default="Save and Exit")

        if not choice or choice == "Save and Exit":
            break
        elif choice == "Global Settings":
            edit_global_settings(config_manager)
        elif choice == "Framework Settings":
            edit_framework_settings(config_manager)
        elif choice == "System Settings":
            edit_system_settings(config_manager)

    # Save configuration
    try:
        config_manager.save_config()
        print_success(f"Configuration saved successfully!")
    except Exception as e:
        print_error(f"Failed to save configuration: {e}")


def edit_global_settings(config_manager: ConfigManager) -> None:
    """Edit global settings"""
    print_info("Editing global settings...")

    # Default model
    current_model = config_manager.config.default_model or "None"
    new_model = prompt_input(
        f"Default model [{current_model}]:",
        default=current_model if current_model != "None" else None
    )
    if new_model:
        config_manager.config.default_model = new_model

    # Default endpoint
    current_endpoint = config_manager.config.default_endpoint
    new_endpoint = prompt_input(
        f"Default endpoint [{current_endpoint}]:",
        default=current_endpoint
    )
    if new_endpoint:
        config_manager.config.default_endpoint = new_endpoint

    # Parallel execution
    current_parallel = config_manager.config.parallel_execution
    new_parallel = prompt_yes_no(
        f"Enable parallel execution?",
        default=current_parallel
    )
    config_manager.config.parallel_execution = new_parallel


def edit_framework_settings(config_manager: ConfigManager) -> None:
    """Edit framework-specific settings"""
    frameworks = ["evalchemy", "standard_evalchemy", "nvidia", "vllm_benchmark", "deepeval"]

    framework = prompt_choice("Select framework to edit:", frameworks)
    if framework:
        edit_framework_config(config_manager, framework)


def edit_framework_config(config_manager: ConfigManager, framework: str) -> None:
    """Edit configuration for a specific framework"""
    print_info(f"Editing {framework} configuration...")

    try:
        framework_config = config_manager.get_framework_config(framework)

        # Enable/disable framework
        enabled = prompt_yes_no(
            f"Enable {framework}?",
            default=framework_config.enabled
        )
        framework_config.enabled = enabled

        if enabled:
            # Edit common settings
            endpoint = prompt_input(
                f"Endpoint [{framework_config.endpoint or 'None'}]:",
                default=framework_config.endpoint
            )
            if endpoint:
                framework_config.endpoint = endpoint

            batch_size = prompt_input(
                f"Batch size [{framework_config.batch_size}]:",
                default=str(framework_config.batch_size),
                validator=lambda x: x.isdigit() and int(x) > 0
            )
            if batch_size:
                framework_config.batch_size = int(batch_size)

            timeout = prompt_input(
                f"Timeout (seconds) [{framework_config.timeout}]:",
                default=str(framework_config.timeout),
                validator=lambda x: x.isdigit() and int(x) > 0
            )
            if timeout:
                framework_config.timeout = int(timeout)

        print_success(f"{framework} configuration updated")

    except Exception as e:
        print_error(f"Failed to edit {framework} configuration: {e}")


def edit_system_settings(config_manager: ConfigManager) -> None:
    """Edit system settings"""
    print_info("Editing system settings...")

    # Results directory
    current_results_dir = str(config_manager.config.system.results_dir)
    new_results_dir = prompt_input(
        f"Results directory [{current_results_dir}]:",
        default=current_results_dir
    )
    if new_results_dir:
        config_manager.config.system.results_dir = Path(new_results_dir)

    # Log level
    log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    current_log_level = config_manager.config.system.log_level
    new_log_level = prompt_choice(
        f"Log level:",
        log_levels,
        default=current_log_level
    )
    if new_log_level:
        config_manager.config.system.log_level = new_log_level


@app.callback()
def config_callback() -> None:
    """⚙️ Manage configuration profiles and settings"""
    pass
