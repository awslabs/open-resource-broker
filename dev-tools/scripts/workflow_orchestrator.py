#!/usr/bin/env python3
"""
Workflow Orchestrator - Consolidated workflow execution.

Orchestrates complete workflows: pre-commit validation, CI pipeline checks.
Consolidates: pre_commit_check.py, ci_check.py workflow logic.
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    import yaml
except ImportError:
    yaml = None


class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    NC = "\033[0m"


def run_hook(name, command, warning_only=False):
    """Run a single hook command."""
    cmd_args = command.split() if isinstance(command, str) else command
    logger.info(f"Running {name}: ", end="", flush=True)

    start_time = time.time()
    result = subprocess.run(cmd_args, check=False, shell=False, capture_output=True, text=True)
    duration = time.time() - start_time

    if result.returncode == 0:
        print(f"{Colors.GREEN}PASS{Colors.NC} ({duration:.1f}s)")
        return True
    else:
        status = (
            f"{Colors.YELLOW}WARN{Colors.NC}" if warning_only else f"{Colors.RED}FAIL{Colors.NC}"
        )
        print(f"{status} ({duration:.1f}s)")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return warning_only


def pre_commit_workflow(required_only=False):
    """Execute pre-commit workflow."""
    config_path = Path(".pre-commit-config.yaml")
    if not config_path.exists():
        logger.error("No .pre-commit-config.yaml found")
        return False

    if yaml is None:
        logger.error("PyYAML not available, using hardcoded hooks")
        # Fallback to hardcoded common hooks
        hooks = ["ruff", "ruff-format", "mypy", "bandit"]
        if not required_only:
            hooks.extend(["hadolint", "actionlint"])
    else:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        hooks = []
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hooks.append(hook["id"])

    success = True
    for hook_id in hooks:
        # Skip optional hooks if required_only
        if required_only and hook_id in ["hadolint", "actionlint"]:
            continue

        # Map hook IDs to commands
        commands = {
            "ruff": "uv run ruff check --quiet .",
            "ruff-format": "uv run ruff format --check --quiet .",
            "mypy": "uv run mypy src",
            "bandit": "uv run bandit -r src -f json -o /tmp/bandit.json || uv run bandit -r src",
            "hadolint": "./dev-tools/scripts/run_tool.sh hadolint Dockerfile",
            "actionlint": "./dev-tools/scripts/run_tool.sh actionlint .github/workflows/*.yml",
        }

        if hook_id in commands:
            warning_only = hook_id in ["hadolint", "actionlint"]
            if not run_hook(hook_id, commands[hook_id], warning_only):
                success = False

    return success


def ci_check_workflow(verbose=False):
    """Execute CI check workflow."""
    logger.info("Running CI checks that match GitHub Actions pipeline...")

    checks = [
        ("Quality - Ruff", "uv run ruff check --quiet ."),
        ("Quality - Format", "uv run ruff format --check --quiet ."),
        ("Quality - MyPy", "uv run mypy src"),
        ("Architecture - CQRS", "./dev-tools/scripts/validate_cqrs.py"),
        ("Architecture - Clean", "./dev-tools/scripts/check_architecture.py"),
        ("Architecture - Imports", "./dev-tools/scripts/validate_imports.py"),
        (
            "Architecture - File Sizes",
            "./dev-tools/scripts/dev_tools_runner.py check-file-sizes --warn-only",
        ),
        (
            "Security - Bandit",
            "uv run bandit -r src -f json -o /tmp/bandit.json || uv run bandit -r src",
        ),
        ("Tests - Unit", "uv run pytest tests/unit -v --tb=short"),
    ]

    success = True
    for name, command in checks:
        if not run_hook(name, command):
            success = False
            if not verbose:
                break

    return success


def main():
    parser = argparse.ArgumentParser(description="Workflow orchestrator")
    parser.add_argument("workflow", choices=["pre-commit", "ci-check"])
    parser.add_argument("--required-only", action="store_true", help="Skip optional checks")
    parser.add_argument("--verbose", action="store_true", help="Continue on failures")

    args = parser.parse_args()

    if args.workflow == "pre-commit":
        success = pre_commit_workflow(args.required_only)
    elif args.workflow == "ci-check":
        success = ci_check_workflow(args.verbose)

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
