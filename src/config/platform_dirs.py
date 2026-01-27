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
    """Get configuration directory location.
    
    Priority:
    1. ORB_CONFIG_DIR environment variable
    2. Development mode detection
    3. User installation
    4. System installation  
    5. Virtual environment
    6. Current directory fallback
    """
    # 1. Environment override
    if env_dir := os.environ.get("ORB_CONFIG_DIR"):
        return Path(env_dir)
    
    # 2. Development mode
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").exists():
            return parent / "config"
    
    # 3. User installation
    if is_user_install():
        return Path.home() / ".local" / "orb" / "config"
    
    # 4. System installation
    if is_system_install():
        return Path(sys.prefix) / "orb" / "config"
    
    # 5. Virtual environment
    if in_virtualenv():
        return Path(sys.prefix).parent / "config"
    
    # 6. Fallback
    return cwd / "config"


def get_work_location() -> Path:
    """Get work directory location.
    
    Priority:
    1. ORB_WORK_DIR environment variable
    2. Relative to configuration directory
    """
    # 1. Environment override
    if env_dir := os.environ.get("ORB_WORK_DIR"):
        return Path(env_dir)
    
    # 2. Relative to config
    return get_config_location().parent / "work"


def get_logs_location() -> Path:
    """Get logs directory location.
    
    Priority:
    1. ORB_LOG_DIR environment variable
    2. Relative to configuration directory
    """
    # 1. Environment override
    if env_dir := os.environ.get("ORB_LOG_DIR"):
        return Path(env_dir)
    
    # 2. Relative to config
    return get_config_location().parent / "logs"


def get_scripts_location() -> Path:
    """Get scripts directory location relative to configuration directory."""
    return get_config_location().parent / "scripts"