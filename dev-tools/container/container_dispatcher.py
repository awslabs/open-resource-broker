#!/usr/bin/env python3
"""Container management dispatcher for the Open Resource Broker."""

import os
import subprocess
import sys


def main():
    args = sys.argv[1:]

    # Parse arguments
    single = "single" in args
    multi = "multi" in args
    push = "push" in args
    run = "run" in args
    version = "version" in args

    if version:
        registry = os.getenv("CONTAINER_REGISTRY", "localhost")
        image = os.getenv("CONTAINER_IMAGE", "open-resource-broker")
        version_val = os.getenv("VERSION", "0.1.0-dev")
        print(f"Container Registry: {registry}")
        print(f"Container Image: {image}")
        print(f"Container Version: {version_val}")
        return 0

    if run:
        try:
            subprocess.run(["./dev-tools/scripts/container_build.sh"], check=True)
            return 0
        except subprocess.CalledProcessError as e:
            return e.returncode

    # Default to single platform build
    if not multi:
        single = True

    if single:
        python_version = os.getenv("PYTHON_VERSION", "3.12")
        registry = os.getenv("CONTAINER_REGISTRY", "localhost")
        image = os.getenv("CONTAINER_IMAGE", "open-resource-broker")
        version_val = os.getenv("VERSION", "0.1.0-dev")

        cmd = [
            "docker",
            "build",
            "--load",
            "--build-arg",
            f"BUILD_DATE={subprocess.check_output(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ']).decode().strip()}",
            "--build-arg",
            f"VERSION={version_val}",
            "--build-arg",
            f"VCS_REF={subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD']).decode().strip()}",
            "--build-arg",
            f"PYTHON_VERSION={python_version}",
            "-t",
            f"{registry}/{image}:{version_val}-python{python_version}",
            ".",
        ]
    else:  # multi
        cmd = ["./dev-tools/scripts/container_build.sh"]
        if push:
            os.environ["PUSH"] = "true"

    try:
        subprocess.run(cmd, check=True)
        return 0
    except subprocess.CalledProcessError as e:
        return e.returncode


if __name__ == "__main__":
    sys.exit(main())
