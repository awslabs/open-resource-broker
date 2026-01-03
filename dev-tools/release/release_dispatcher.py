#!/usr/bin/env python3
"""Release management dispatcher for the Open Resource Broker."""

import subprocess
import sys


def parse_args(args):
    """Parse command line arguments."""
    return {
        "patch": "patch" in args,
        "minor": "minor" in args,
        "major": "major" in args,
        "alpha": "alpha" in args,
        "beta": "beta" in args,
        "rc": "rc" in args,
    }


def get_release_type(parsed):
    """Get release type from parsed arguments."""
    if parsed["patch"]:
        return "patch"
    elif parsed["minor"]:
        return "minor"
    elif parsed["major"]:
        return "major"
    return None


def get_prerelease_type(parsed):
    """Get prerelease type from parsed arguments."""
    if parsed["alpha"]:
        return "alpha"
    elif parsed["beta"]:
        return "beta"
    elif parsed["rc"]:
        return "rc"
    return None


def build_release_cmd(release_type, prerelease_type):
    """Build release command."""
    cmd = ["./dev-tools/release/create_release.sh", release_type]
    if prerelease_type:
        cmd.append(prerelease_type)
    return cmd


def main():
    parsed = parse_args(sys.argv[1:])
    release_type = get_release_type(parsed)

    if not release_type:
        print("Error: Must specify release type (patch, minor, or major)")
        return 1

    prerelease_type = get_prerelease_type(parsed)
    cmd = build_release_cmd(release_type, prerelease_type)

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
