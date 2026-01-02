#!/usr/bin/env python3
"""
Development Tools Runner - Consolidated simple tool wrappers.

Consolidates: clean_whitespace.py, check_file_sizes.py, venv_setup.py, hadolint_check.py, deps_manager.py
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

try:
    import pathspec
except ImportError:
    pathspec = None


def clean_whitespace():
    """Clean whitespace from Python files."""

    def load_gitignore_spec(root_dir: Path):
        if pathspec is None:
            return None
        gitignore_path = root_dir / ".gitignore"
        if gitignore_path.exists():
            with open(gitignore_path, encoding="utf-8") as f:
                return pathspec.PathSpec.from_lines("gitwildmatch", f)
        return pathspec.PathSpec.from_lines("gitwildmatch", [])

    def clean_file(file_path: Path) -> bool:
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            original_content = content
            lines = content.splitlines()
            cleaned_lines = [line.rstrip() for line in lines]
            if cleaned_lines and cleaned_lines[-1]:
                cleaned_lines.append("")
            cleaned_content = "\n".join(cleaned_lines)
            if cleaned_content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(cleaned_content)
                return True
            return False
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False

    root_dir = Path.cwd()
    gitignore_spec = load_gitignore_spec(root_dir)

    files_cleaned = 0
    for file_path in root_dir.rglob("*.py"):
        # Skip .venv and other common directories
        if any(
            part in [".venv", ".git", "__pycache__", "node_modules", ".pytest_cache"]
            for part in file_path.parts
        ):
            continue
        # Skip if gitignore available and file matches
        if gitignore_spec and gitignore_spec.match_file(str(file_path.relative_to(root_dir))):
            continue
        if clean_file(file_path):
            files_cleaned += 1
            logger.info(f"Cleaned: {file_path}")

    logger.info(f"Cleaned {files_cleaned} files")


def check_file_sizes(warn_only=False, threshold=600):
    """Check for files that are getting too large."""
    large_files = []

    src_dir = Path("src")
    if not src_dir.exists():
        logger.warning("src/ directory not found, skipping file size check")
        return

    for file_path in src_dir.rglob("*.py"):
        try:
            line_count = len(file_path.read_text(encoding="utf-8").splitlines())
            if line_count > threshold:
                large_files.append((file_path, line_count))
        except Exception as e:
            logger.warning(f"Could not read {file_path}: {e}")

    if large_files:
        logger.warning(f"Found {len(large_files)} files over {threshold} lines:")
        for file_path, line_count in sorted(large_files, key=lambda x: x[1], reverse=True):
            logger.warning(f"  {file_path}: {line_count} lines")

        if not warn_only:
            logger.error("Large files detected. Consider refactoring.")
            sys.exit(1)
    else:
        logger.info(f"All files are under {threshold} lines")


def venv_setup():
    """Setup virtual environment with uv or pip fallback."""
    venv_dir = Path(".venv")
    python_exe = sys.executable

    # Create venv if it doesn't exist
    if not venv_dir.exists():
        logger.info("Creating virtual environment...")
        subprocess.run([python_exe, "-m", "venv", str(venv_dir)], check=True)

    # Determine pip path
    if sys.platform == "win32":
        pip_path = venv_dir / "Scripts" / "pip"
    else:
        pip_path = venv_dir / "bin" / "pip"

    # Upgrade pip using uv or pip
    if shutil.which("uv"):
        logger.info("Using uv for virtual environment setup...")
        subprocess.run(["uv", "pip", "install", "--upgrade", "pip"], check=True)
    else:
        logger.info("Using pip for virtual environment setup...")
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True)

    # Touch activate file
    if sys.platform == "win32":
        activate_file = venv_dir / "Scripts" / "activate"
    else:
        activate_file = venv_dir / "bin" / "activate"

    activate_file.touch()
    logger.info("Virtual environment setup complete!")


def hadolint_check(files=None, install_help=False):
    """Check Dockerfiles with hadolint."""
    if install_help:
        logger.info("Install hadolint:")
        logger.info("  macOS: brew install hadolint")
        logger.info("  Linux: See https://github.com/hadolint/hadolint#install")
        return

    if not shutil.which("hadolint"):
        logger.error("Error: hadolint not found")
        logger.info("Install with: brew install hadolint")
        return False

    # Default files to check
    files = files or ["Dockerfile", "dev-tools/docker/Dockerfile.dev-tools"]

    exit_code = 0
    for file_path in files:
        dockerfile = Path(file_path)
        if not dockerfile.exists():
            logger.warning(f"Warning: {dockerfile} not found, skipping")
            continue

        logger.info(f"Checking {dockerfile} with hadolint...")
        try:
            subprocess.run(["hadolint", str(dockerfile)], check=True)
        except subprocess.CalledProcessError:
            logger.info(f"Hadolint found issues in {dockerfile}")
            exit_code = 1

    if exit_code == 0:
        logger.info("All Dockerfiles passed hadolint checks!")
    return exit_code == 0


def deps_add(package, dev=False):
    """Add a dependency using uv."""
    if not package:
        logger.error("Error: Package name is required")
        return False

    cmd = ["uv", "add"]
    if dev:
        cmd.append("--dev")
    cmd.append(package)

    logger.info(f"Adding {'dev ' if dev else ''}dependency: {package}")
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to add dependency: {e}")
        return False
    except FileNotFoundError:
        logger.error("Command not found: uv")
        return False


def has_sudo_access():
    """Check if current user has sudo access."""
    try:
        # Test sudo access without password prompt
        result = subprocess.run(
            ["sudo", "-n", "true"], 
            capture_output=True, 
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def print_installation_summary(install_type, install_dir, binary_path=None):
    """Print comprehensive installation summary."""
    import os
    
    print("\n" + "="*50)
    print("INSTALLATION COMPLETE")
    print("="*50)
    print(f"Installation type: {install_type}")
    print(f"Location: {install_dir}")
    
    if install_type == "system":
        print(f"Binary installed: {install_dir}/bin/orb")
        print(f"Tools directory: {install_dir}/tools")
        print(f"Config directory: {install_dir}/config")
        print(f"Logs directory: {install_dir}/logs")
        print("\nNEXT STEPS:")
        print(f"1. Add to PATH: export PATH=\"{install_dir}/bin:$PATH\"")
        print(f"2. Place config files in: {install_dir}/config/")
        print(f"3. Logs will be written to: {install_dir}/logs/")
        print("4. Test installation: orb --version")
        
        # Check if directory is in PATH
        current_path = os.environ.get("PATH", "")
        bin_dir = f"{install_dir}/bin"
        if bin_dir not in current_path:
            print(f"\nWARNING: {bin_dir} is not in your PATH")
            print("Add this to your shell profile (.bashrc, .zshrc, etc.):")
            print(f"  export PATH=\"{bin_dir}:$PATH\"")
    
    elif install_type == "local development":
        if binary_path and Path(binary_path).exists():
            print(f"Binary available: {binary_path}")
        print("Virtual environment: .venv/")
        print("Python packages: Installed in .venv/lib/python*/site-packages/")
        print("\nNEXT STEPS:")
        print("1. Activate environment: source .venv/bin/activate")
        print("2. Test installation: orb --version")
        print("3. Start development: make dev")
        
        # Check if .venv/bin is in PATH
        current_path = os.environ.get("PATH", "")
        venv_bin = f"{install_dir}/.venv/bin"
        if venv_bin not in current_path:
            print(f"\nNOTE: For direct access without activation:")
            print(f"  export PATH=\"{venv_bin}:$PATH\"")
    
    print("="*50)


def cleanup_empty_directories(install_dir):
    """Clean up empty installation directories."""
    try:
        for subdir in ["bin", "tools", "config", "logs"]:
            dir_path = Path(f"{install_dir}/{subdir}")
            if dir_path.exists() and not any(dir_path.iterdir()):
                dir_path.rmdir()
        
        # Remove main directory if empty
        main_dir = Path(install_dir)
        if main_dir.exists() and not any(main_dir.iterdir()):
            main_dir.rmdir()
            print(f"Removed empty directory: {install_dir}")
    except OSError:
        pass  # Directory not empty or permission issues


def system_uninstall():
    """Smart system-wide uninstall - detects installation location."""
    import os
    
    # Check common locations for orb binary
    locations = [
        "/usr/local/orb",
        os.path.expanduser("~/.local/orb"),
        os.environ.get("ORB_INSTALL_DIR")
    ]
    
    found_installations = []
    for location in locations:
        if location and Path(f"{location}/bin/orb").exists():
            found_installations.append(location)
    
    if not found_installations:
        print("No system installations found")
        return
    
    print(f"Found installations at: {', '.join(found_installations)}")
    
    # Use uv tool uninstall (works regardless of installation location)
    try:
        subprocess.run(["uv", "tool", "uninstall", "open-resource-broker"], check=True)
        print("System installation removed successfully")
        
        # Clean up directories if empty
        for location in found_installations:
            cleanup_empty_directories(location)
            
    except subprocess.CalledProcessError as e:
        print(f"Failed to uninstall via uv tool: {e}")
        sys.exit(1)


def local_uninstall():
    """Remove local development environment."""
    import shutil
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        shutil.rmtree(venv_path)
        print("Local development environment removed (.venv deleted)")
    else:
        print("No local development environment found")


def uninstall_all():
    """Remove all installations (system + local + PyPI)."""
    print("Removing all Open Resource Broker installations...")
    
    system_uninstall()
    local_uninstall()
    
    # Also try pip uninstall for PyPI installations
    try:
        subprocess.run(["pip", "uninstall", "open-resource-broker", "-y"], 
                      capture_output=True, check=True)
        print("PyPI installation removed")
    except subprocess.CalledProcessError:
        pass  # Not installed via pip
    
    print("All installations removed")


def system_install():
    """Install system-wide with smart directory selection."""
    import os
    
    # Check if custom directory specified
    custom_dir = os.environ.get("ORB_INSTALL_DIR")
    
    if custom_dir:
        install_dir = custom_dir
        print(f"Using custom installation directory: {install_dir}")
    else:
        # Auto-detect best installation directory
        if has_sudo_access():
            install_dir = "/usr/local/orb"
            print("Detected sudo access - installing to /usr/local/orb")
        else:
            install_dir = os.path.expanduser("~/.local/orb")
            print("No sudo access - installing to ~/.local/orb")
    
    print(f"Installing Open Resource Broker to {install_dir}...")
    
    # Create directory structure
    Path(f"{install_dir}/bin").mkdir(parents=True, exist_ok=True)
    Path(f"{install_dir}/tools").mkdir(parents=True, exist_ok=True)
    Path(f"{install_dir}/config").mkdir(parents=True, exist_ok=True)
    Path(f"{install_dir}/logs").mkdir(parents=True, exist_ok=True)
    
    # Set environment and install
    env = os.environ.copy()
    env["UV_TOOL_DIR"] = f"{install_dir}/tools"
    env["UV_TOOL_BIN_DIR"] = f"{install_dir}/bin"
    
    try:
        subprocess.run(["uv", "tool", "install", "."], env=env, check=True)
        print_installation_summary("system", install_dir)
    except subprocess.CalledProcessError as e:
        print(f"Installation failed: {e}")
        sys.exit(1)


def local_install():
    """Install local development environment with feedback."""
    import os
    
    current_dir = Path.cwd()
    venv_path = current_dir / ".venv"
    binary_path = venv_path / "bin" / "orb"
    
    print("Installing local development environment...")
    
    # Use uv if available, otherwise pip
    try:
        if shutil.which("uv"):
            print("Using uv for installation...")
            subprocess.run(["uv", "sync", "--no-dev"], check=True, capture_output=True)
        else:
            print("Using pip for installation...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], check=True, capture_output=True)
        
        print_installation_summary("local development", str(current_dir), str(binary_path))
    except subprocess.CalledProcessError as e:
        print(f"Local installation failed: {e}")
        sys.exit(1)


def dev_install():
    """Install development environment with all dependencies and feedback."""
    import os
    
    current_dir = Path.cwd()
    venv_path = current_dir / ".venv"
    binary_path = venv_path / "bin" / "orb"
    
    print("Installing development environment with all dependencies...")
    
    # Use uv if available, otherwise pip
    try:
        if shutil.which("uv"):
            print("Using uv for installation...")
            subprocess.run(["uv", "sync", "--all-groups"], check=True, capture_output=True)
        else:
            print("Using pip for installation...")
            subprocess.run([sys.executable, "-m", "pip", "install", "-e", ".[dev]"], check=True, capture_output=True)
        
        print_installation_summary("local development", str(current_dir), str(binary_path))
    except subprocess.CalledProcessError as e:
        print(f"Development installation failed: {e}")
        sys.exit(1)


def system_uninstall():
    """Smart system-wide uninstall - detects installation location."""
    import os
    import shutil
    
    # Check common locations for orb binary
    locations = [
        "/usr/local/orb",
        os.path.expanduser("~/.local/orb"),
        os.environ.get("ORB_INSTALL_DIR")
    ]
    
    found_installations = []
    for location in locations:
        if location and Path(f"{location}/bin/orb").exists():
            found_installations.append(location)
    
    if not found_installations:
        print("No system installations found")
        return
    
    print(f"Found installations at: {', '.join(found_installations)}")
    
    # Try uv tool uninstall first
    try:
        subprocess.run(["uv", "tool", "uninstall", "open-resource-broker"], 
                      capture_output=True, check=True)
        print("Removed via uv tool uninstall")
    except subprocess.CalledProcessError:
        # Fallback: manually remove directories
        print("uv tool uninstall failed, removing directories manually...")
        for location in found_installations:
            try:
                shutil.rmtree(location)
                print(f"Removed directory: {location}")
            except OSError as e:
                print(f"Failed to remove {location}: {e}")
                continue
    
    print("System installation removed successfully")


def local_uninstall():
    """Remove local development environment."""
    import shutil
    
    venv_path = Path(".venv")
    
    if venv_path.exists():
        shutil.rmtree(venv_path)
        print("Local development environment removed (.venv deleted)")
    else:
        print("No local development environment found")


def uninstall_all():
    """Remove all installations (system + local + PyPI)."""
    print("Removing all Open Resource Broker installations...")
    
    system_uninstall()
    local_uninstall()
    
    # Also try pip uninstall for PyPI installations
    try:
        subprocess.run(["pip", "uninstall", "open-resource-broker", "-y"], 
                      capture_output=True, check=True)
        print("PyPI installation removed")
    except subprocess.CalledProcessError:
        pass  # Not installed via pip
    
    print("All installations removed")


def main():
    parser = argparse.ArgumentParser(description="Development tools runner")
    parser.add_argument(
        "command",
        choices=[
            "clean-whitespace",
            "check-file-sizes",
            "venv-setup",
            "hadolint-check",
            "deps-add",
            "system-install",
            "local-install", 
            "dev-install",
            "system-uninstall",
            "local-uninstall",
            "uninstall-all",
        ],
    )
    parser.add_argument("--warn-only", action="store_true", help="Only warn, don't fail")
    parser.add_argument("--threshold", type=int, default=600, help="Line count threshold")
    parser.add_argument("--install-help", action="store_true", help="Show installation help")
    parser.add_argument("--dev", action="store_true", help="Add as dev dependency")
    parser.add_argument("files", nargs="*", help="Files to process")

    args = parser.parse_args()

    if args.command == "clean-whitespace":
        clean_whitespace()
    elif args.command == "check-file-sizes":
        check_file_sizes(warn_only=args.warn_only, threshold=args.threshold)
    elif args.command == "venv-setup":
        venv_setup()
    elif args.command == "hadolint-check":
        success = hadolint_check(files=args.files, install_help=args.install_help)
        if not success and not args.install_help:
            sys.exit(1)
    elif args.command == "deps-add":
        if not args.files:
            logger.error("Package name required for deps-add")
            sys.exit(1)
        success = deps_add(args.files[0], dev=args.dev)
        if not success:
            sys.exit(1)
    elif args.command == "system-install":
        system_install()
    elif args.command == "local-install":
        local_install()
    elif args.command == "dev-install":
        dev_install()
    elif args.command == "system-uninstall":
        system_uninstall()
    elif args.command == "local-uninstall":
        local_uninstall()
    elif args.command == "uninstall-all":
        uninstall_all()


if __name__ == "__main__":
    main()
