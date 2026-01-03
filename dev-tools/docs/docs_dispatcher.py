#!/usr/bin/env python3
"""Documentation dispatcher for the Open Resource Broker."""

import os
import subprocess
import sys


def main():
    args = sys.argv[1:]

    # Parse arguments
    serve = "serve" in args
    deploy = "deploy" in args
    version = any(arg.startswith("version=") for arg in args)
    list_versions = "list" in args
    delete = any(arg.startswith("delete=") for arg in args)
    clean = "clean" in args

    if clean:
        docs_build_dir = os.getenv("DOCS_BUILD_DIR", "docs/site")
        subprocess.run(["rm", "-rf", docs_build_dir], check=True)
        print(f"Cleaned {docs_build_dir}")
        return 0

    if list_versions:
        cmd = ["./dev-tools/scripts/run_tool.sh", "mike", "list"]
        subprocess.run(cmd, cwd="docs", check=True)
        return 0

    if delete:
        version_to_delete = next(
            (arg.split("=")[1] for arg in args if arg.startswith("delete=")), None
        )
        if not version_to_delete:
            print("ERROR: delete requires version (e.g., delete=1.0.0)")
            return 1
        cmd = ["./dev-tools/scripts/run_tool.sh", "mike", "delete", version_to_delete]
        subprocess.run(cmd, cwd="docs", check=True)
        return 0

    if serve:
        print("Starting documentation server at http://127.0.0.1:8000")
        print("Press Ctrl+C to stop the server")
        cmd = ["./dev-tools/scripts/run_tool.sh", "mike", "serve"]
        subprocess.run(cmd, cwd="docs", check=True)
        return 0

    if deploy:
        if version:
            version_num = next(
                (arg.split("=")[1] for arg in args if arg.startswith("version=")), None
            )
            if not version_num:
                print("ERROR: deploy with version requires version=X.X.X")
                return 1
            # Configure git for CI if needed
            if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
                subprocess.run(
                    ["git", "config", "--global", "user.name", "github-actions[bot]"], check=True
                )
                subprocess.run(
                    [
                        "git",
                        "config",
                        "--global",
                        "user.email",
                        "github-actions[bot]@users.noreply.github.com",
                    ],
                    check=True,
                )
            cmd = [
                "./dev-tools/scripts/run_tool.sh",
                "mike",
                "deploy",
                "--push",
                "--update-aliases",
                version_num,
                "latest",
            ]
        # Local deploy
        elif os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
            subprocess.run(["make", "ci-docs-deploy"], check=True)
        else:
            print("WARNING: This will commit to your local gh-pages branch")
            cmd = [
                "./dev-tools/scripts/run_tool.sh",
                "mike",
                "deploy",
                "--update-aliases",
                "latest",
            ]
            subprocess.run(cmd, cwd="docs", check=True)
            print("Documentation deployed locally. Use 'git push origin gh-pages' to publish.")
        return 0

    # Default: build
    if os.getenv("CI") or os.getenv("GITHUB_ACTIONS"):
        subprocess.run(["make", "ci-docs-build"], check=True)
    else:
        print("Building documentation locally with mike...")
        cmd = ["./dev-tools/scripts/run_tool.sh", "mike", "deploy", "--update-aliases", "latest"]
        subprocess.run(cmd, cwd="docs", check=True)
        print("Documentation built with mike versioning")

    return 0


if __name__ == "__main__":
    sys.exit(main())
