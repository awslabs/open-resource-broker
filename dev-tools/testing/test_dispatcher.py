#!/usr/bin/env python3
"""Test runner dispatcher for the Open Resource Broker."""

import subprocess
import sys


def parse_args(args):
    """Parse command line arguments."""
    test_type = None
    coverage = False
    parallel = False
    fast = False
    markers = None
    files = []

    for arg in args:
        if arg == "unit":
            test_type = "tests/unit"
        elif arg == "integration":
            test_type = "tests/integration"
        elif arg == "e2e":
            test_type = "tests/e2e"
        elif arg == "onaws":
            test_type = "tests/onaws"
        elif arg == "all":
            test_type = "tests"
        elif arg == "coverage":
            coverage = True
        elif arg == "html-coverage":
            coverage = True
        elif arg == "parallel":
            parallel = True
        elif arg == "fast":
            fast = True
        elif arg == "performance":
            markers = "slow"
        elif arg == "aws":
            markers = "aws"
        elif arg.endswith(".py") or "/" in arg:
            files.append(arg)

    return {
        "test_type": test_type,
        "coverage": coverage,
        "parallel": parallel,
        "fast": fast,
        "markers": markers,
        "files": files,
        "html_coverage": "html-coverage" in args,
    }


def build_pytest_cmd(parsed):
    """Build pytest command from parsed arguments."""
    cmd = ["uv", "run", "pytest"]

    # Add test scope
    if parsed["test_type"]:
        cmd.append(parsed["test_type"])
    elif parsed["files"]:
        cmd.extend(parsed["files"])
    else:
        cmd.append("tests/unit")

    # Add options
    cmd.extend(["-v", "--tb=short", "--durations=10"])

    if parsed["coverage"]:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-branch"])
        if parsed["html_coverage"]:
            cmd.append("--cov-report=html")

    if parsed["parallel"]:
        cmd.extend(["-n", "auto"])

    if parsed["fast"]:
        cmd.append("--maxfail=5")

    if parsed["markers"]:
        cmd.extend(["-m", parsed["markers"]])

    cmd.extend(["--timeout=300", "--maxfail=5"])
    return cmd


def main():
    parsed = parse_args(sys.argv[1:])
    cmd = build_pytest_cmd(parsed)

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
