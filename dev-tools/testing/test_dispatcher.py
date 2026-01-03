#!/usr/bin/env python3
"""Test runner dispatcher for the Open Resource Broker."""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    # Build pytest command
    cmd = ["uv", "run", "pytest"]

    # Parse arguments
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

    # Add test scope
    if test_type:
        cmd.append(test_type)
    elif files:
        cmd.extend(files)
    else:
        cmd.append("tests/unit")

    # Add options
    cmd.extend(["-v", "--tb=short", "--durations=10"])

    if coverage:
        cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-branch"])
        if "html-coverage" in args:
            cmd.append("--cov-report=html")

    if parallel:
        cmd.extend(["-n", "auto"])

    if fast:
        cmd.append("--maxfail=5")

    if markers:
        cmd.extend(["-m", markers])

    cmd.extend(["--timeout=300", "--maxfail=5"])

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
