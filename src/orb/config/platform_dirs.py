"""Platform-specific directory detection for ORB configuration."""

import os
import site
import sys
from pathlib import Path

from orb.config.installation_detector import detect_install_mode


def _get_root_dir() -> Path | None:
    """Return ORB_ROOT_DIR as a Path if set, else None."""
    if root := os.environ.get("ORB_ROOT_DIR"):
        return Path(root)
    return None


def in_virtualenv() -> bool:
    """Check if running in a virtual environment.

    Handles both standard venvs (sys.prefix != sys.base_prefix) and
    symlink-based venvs like uv/mise (sys.executable not in sys.prefix).
    """
    # Standard venv detection
    if sys.prefix != sys.base_prefix:
        return True

    # Symlink venv detection (project-local .venv only)
    # Don't resolve symlinks - we want to check the actual executable location
    executable_path = Path(sys.executable)  # Don't resolve!
    prefix_path = Path(sys.prefix)

    try:
        # Check if executable is under prefix
        executable_path.relative_to(prefix_path)
        return False  # Executable is under prefix, not a venv
    except ValueError:
        # Executable is outside prefix — only treat as symlink-venv if the
        # executable path actually contains a .venv directory component.
        # This excludes mise (~/.local/share/mise/...) and similar tools.
        if ".venv" in executable_path.parts:
            return True
        return False


def is_user_install() -> bool:
    """Check if this is a user install (pip install --user)."""
    user_base = getattr(site, "USER_BASE", None)
    if user_base and str(sys.prefix).startswith(user_base):
        return True
    return False


def is_system_install() -> bool:
    """Check if this is a system install."""
    return sys.prefix.startswith(("/usr", "/opt"))


def get_config_location() -> Path:
    """Get basic configuration directory location for bootstrap."""
    # 1. Environment override
    if env_dir := os.environ.get("ORB_CONFIG_DIR"):
        return Path(env_dir)

    # 2. ORB_ROOT_DIR
    if root := _get_root_dir():
        return root / "config"

    # 3. Delegate to unified install-mode detector
    mode = detect_install_mode()

    if mode == "uv_tool":
        return Path.home() / ".local" / "orb" / "config"

    if mode == "venv":
        # Standard venv: sys.prefix is the venv directory
        return Path(sys.prefix).parent / "config"

    if mode in ("development", "editable"):
        cwd = Path.cwd()
        for parent in [cwd] + list(cwd.parents):
            if (parent / "pyproject.toml").exists():
                return parent / "config"
        return cwd / "config"

    if mode == "user":
        return Path.home() / ".local" / "orb" / "config"

    if mode == "system":
        return Path(sys.prefix) / "orb" / "config"

    # Fallback
    return Path.cwd() / "config"


def get_work_location() -> Path:
    """Get basic work directory location for bootstrap."""
    # 1. Environment override
    if env_dir := os.environ.get("ORB_WORK_DIR"):
        return Path(env_dir)

    # 2. ORB_ROOT_DIR
    if root := _get_root_dir():
        return root / "work"

    # 3. Relative to config
    return get_config_location().parent / "work"


def get_logs_location() -> Path:
    """Get basic logs directory location for bootstrap."""
    # 1. Environment override
    if env_dir := os.environ.get("ORB_LOG_DIR"):
        return Path(env_dir)

    # 2. ORB_ROOT_DIR
    if root := _get_root_dir():
        return root / "logs"

    # 3. Relative to config
    return get_config_location().parent / "logs"


def get_scripts_location() -> Path:
    """Get basic scripts directory location for bootstrap."""
    # 1. Environment override
    if env_dir := os.environ.get("ORB_SCRIPTS_DIR"):
        return Path(env_dir)

    # 2. ORB_ROOT_DIR
    if root := _get_root_dir():
        return root / "scripts"

    # 3. Relative to config
    return get_config_location().parent / "scripts"


def get_health_location() -> Path:
    """Get health check directory location.

    Precedence:
    1. ORB_HEALTH_DIR env var
    2. ORB_ROOT_DIR/health
    3. Sibling of config dir (get_config_location().parent / 'health')
    """
    # 1. Environment override
    if env_dir := os.environ.get("ORB_HEALTH_DIR"):
        return Path(env_dir)

    # 2. ORB_ROOT_DIR
    if root := _get_root_dir():
        return root / "health"

    # 3. Sibling of config dir
    return get_config_location().parent / "health"
