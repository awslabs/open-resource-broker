"""Shared Rich console for CLI output."""

import os
import sys
from functools import wraps
from rich.console import Console

# Singleton console instances
_console = Console()
_error_console = Console(stderr=True)


def _should_print() -> bool:
    """Check if console output is enabled.
    
    Respects LOG_CONSOLE_ENABLED environment variable.
    HostFactory sets this to false to get JSON-only output.
    """
    return os.environ.get("LOG_CONSOLE_ENABLED", "true").lower() == "true"


def _console_output(func):
    """Decorator to check if console output is enabled before printing."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if _should_print():
            return func(*args, **kwargs)
    return wrapper


def get_console() -> Console:
    """Get the shared Rich console instance."""
    return _console


@_console_output
def print_success(message: str):
    """Print success message in green."""
    _console.print(f"[green]{message}[/green]")


@_console_output
def print_error(message: str):
    """Print error message in red to stderr."""
    _error_console.print(f"[red]{message}[/red]")


@_console_output
def print_info(message: str):
    """Print info message in cyan."""
    _console.print(f"[cyan]{message}[/cyan]")


@_console_output
def print_warning(message: str):
    """Print warning message in yellow."""
    _console.print(f"[yellow]{message}[/yellow]")


@_console_output
def print_command(message: str):
    """Print command in yellow."""
    _console.print(f"[yellow]{message}[/yellow]")


@_console_output
def print_separator(width: int = 60, char: str = "━", color: str = "green"):
    """Print colored separator line."""
    _console.print(f"[{color}]{char * width}[/{color}]")


@_console_output
def print_section(title: str, width: int = 60):
    """Print section header with separator."""
    _console.print(f"\n[cyan]{title}[/cyan]")
    _console.print(f"[cyan]{'-' * width}[/cyan]")
