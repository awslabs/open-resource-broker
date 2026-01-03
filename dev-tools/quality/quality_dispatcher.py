#!/usr/bin/env python3
"""Quality check dispatcher for the Open Resource Broker."""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    # Parse arguments
    check_all = "all" in args
    fix_mode = "fix" in args
    files = [arg for arg in args if arg.endswith(".py") or "/" in arg]

    success = True

    # Run whitespace cleanup first if fixing
    if fix_mode:
        try:
            subprocess.run(
                ["./dev-tools/scripts/dev_tools_runner.py", "clean-whitespace"], check=True
            )
        except subprocess.CalledProcessError:
            success = False

    # Run ruff format
    ruff_format_cmd = ["uv", "run", "ruff", "format"]
    if not fix_mode:
        ruff_format_cmd.append("--check")
    ruff_format_cmd.append("--quiet")

    if files:
        ruff_format_cmd.extend(files)
    else:
        ruff_format_cmd.append(".")

    try:
        subprocess.run(ruff_format_cmd, check=True)
    except subprocess.CalledProcessError:
        success = False

    # Run ruff check
    ruff_check_cmd = ["uv", "run", "ruff", "check"]
    if fix_mode:
        ruff_check_cmd.extend(["--fix", "--exit-zero"])
    ruff_check_cmd.append("--quiet")

    if files:
        ruff_check_cmd.extend(files)
    else:
        ruff_check_cmd.append(".")

    try:
        subprocess.run(ruff_check_cmd, check=True)
    except subprocess.CalledProcessError:
        success = False

    # Run additional checks if all mode
    if check_all:
        try:
            subprocess.run(
                ["python3", "./dev-tools/scripts/quality_check.py", "--strict", "--all"], check=True
            )
        except subprocess.CalledProcessError:
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
