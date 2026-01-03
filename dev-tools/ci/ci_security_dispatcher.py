#!/usr/bin/env python3
"""CI Security dispatcher for the Open Resource Broker."""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    if not args:
        print(
            "ERROR: Security tool required (bandit, safety, trivy, hadolint, semgrep, trivy-fs, trufflehog)"
        )
        return 1

    tool = args[0]

    if tool == "bandit":
        print("Running Bandit security scan...")
        cmd = ["./dev-tools/scripts/run_tool.sh", "bandit", "-r", "src"]

    elif tool == "safety":
        print("Running Safety dependency scan...")
        cmd = ["./dev-tools/scripts/run_tool.sh", "safety", "check"]

    elif tool in ["trivy", "hadolint", "semgrep", "trivy-fs", "trufflehog"]:
        # These use the existing ci_security.py script
        cmd = ["./dev-tools/scripts/ci_security.py", tool]

    else:
        print(f"ERROR: Unknown security tool: {tool}")
        return 1

    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
