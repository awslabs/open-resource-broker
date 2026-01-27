"""Platform-specific directory detection for ORB configuration."""

import os
import sys
from pathlib import Path


def in_virtualenv() -> bool:
    """Check if running in a virtual environment."""
    return sys.prefix != sys.base_prefix


def is_user_install() -> bool:
    """Check if this is a user install (pip install --user)."""
    return sys.prefix.startswith(str(Path.home()))


def is_system_install() -> bool:
    """Check if this is a system install."""
    return sys.prefix.startswith(("/usr", "/opt"))


def get_config_location() -> Path:
    """Get config location.
    
    Priority:
    1. ORB_CONFIG_DIR environment variable (standard)
    2. Development: ./config if pyproject.toml exists in parent chain
    3. User install: ~/.local/orb/config
    4. System install: /usr/local/orb/config or /opt/orb/config
    5. Virtualenv: sibling to venv
    6. Fallback: current directory
    """
    # 1. Standard ORB environment variable
    if env_dir := os.environ.get("ORB_CONFIG_DIR"):
        return Path(env_dir)
    
    # 2. Development mode - check parent directories for pyproject.toml
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").exists():
            return parent / "config"
    
    # 3. User install (pip install --user)
    if is_user_install():
        return Path.home() / ".local" / "orb" / "config"
    
    # 4. System install
    if is_system_install():
        return Path(sys.prefix) / "orb" / "config"
    
    # 5. Virtualenv - config sibling to venv
    if in_virtualenv():
        return Path(sys.prefix).parent / "config"
    
    # 6. Fallback
    return cwd / "config"


def get_work_location() -> Path:
    """Get work directory location.
    
    Priority:
    1. ORB_WORK_DIR environment variable (standard)
    2. Sibling to config directory
    """
    # 1. Standard ORB environment variable
    if env_dir := os.environ.get("ORB_WORK_DIR"):
        return Path(env_dir)
    
    # 2. Default: sibling to config
    return get_config_location().parent / "work"


def get_logs_location() -> Path:
    """Get logs directory location.
    
    Priority:
    1. ORB_LOG_DIR environment variable (standard)
    2. Sibling to config directory
    """
    # 1. Standard ORB environment variable
    if env_dir := os.environ.get("ORB_LOG_DIR"):
        return Path(env_dir)
    
    # 2. Default: sibling to config
    return get_config_location().parent / "logs"


def get_scripts_location() -> Path:
    """Get scripts directory location.
    
    For HostFactory: Could use HF_PROVIDER_SCRIPTDIR if set (future)
    Otherwise: Sibling to config directory
    """
    if env_dir := os.environ.get("HF_PROVIDER_SCRIPTDIR"):
        return Path(env_dir)
    
    return get_config_location().parent / "scripts"