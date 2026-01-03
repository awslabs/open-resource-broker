#!/usr/bin/env python3
"""Release management dispatcher for the Open Resource Broker."""

import subprocess
import sys


def main():
    args = sys.argv[1:]

    # Parse arguments
    patch = "patch" in args
    minor = "minor" in args
    major = "major" in args
    alpha = "alpha" in args
    beta = "beta" in args
    rc = "rc" in args

    if not any([patch, minor, major]):
        print("Error: Must specify release type (patch, minor, or major)")
        return 1

    # Build release command
    cmd = ["./dev-tools/release/create_release.sh"]

    if patch:
        cmd.append("patch")
    elif minor:
        cmd.append("minor")
    elif major:
        cmd.append("major")

    if alpha:
        cmd.append("alpha")
    elif beta:
        cmd.append("beta")
    elif rc:
        cmd.append("rc")

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
