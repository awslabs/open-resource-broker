"""Platform-specific directory detection for ORB configuration."""

import os
import sys
from pathlib import Path


def in_virtualenv() -> bool:
    """Check if running in a virtual environment."""
    return sys.prefix != sys.base_prefix


def get_config_location() -> Path:
    """Get config location.
    
    Priority:
    1. HF_PROVIDER_CONFDIR environment variable (HostFactory)
    2. Virtualenv: sibling to venv
    3. Development: ./config if pyproject.toml exists in parent chain
    """
    # 1. HostFactory environment variable
    if env_dir := os.environ.get("HF_PROVIDER_CONFDIR"):
        return Path(env_dir)
    
    # 2. Virtualenv - config sibling to venv
    if in_virtualenv():
        return Path(sys.prefix).parent / "config"
    
    # 3. Development mode - check parent directories for pyproject.toml
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / "pyproject.toml").exists():
            return parent / "config"
    
    # If none of the above, use current directory
    return cwd / "config"


def get_work_location() -> Path:
    """Get work directory location.
    
    For HostFactory: Uses HF_PROVIDER_WORKDIR if set
    Otherwise: Sibling to config directory
    """
    # HostFactory environment variable
    if env_dir := os.environ.get("HF_PROVIDER_WORKDIR"):
        return Path(env_dir)
    
    # Default: sibling to config
    return get_config_location().parent / "work"


def get_logs_location() -> Path:
    """Get logs directory location.
    
    For HostFactory: Uses HF_PROVIDER_LOGDIR if set
    Otherwise: Sibling to config directory
    """
    if env_dir := os.environ.get("HF_PROVIDER_LOGDIR"):
        return Path(env_dir)
    
    return get_config_location().parent / "logs"


def get_scripts_location() -> Path:
    """Get scripts directory location.
    
    For HostFactory: Could use HF_PROVIDER_SCRIPTDIR if set (future)
    Otherwise: Sibling to config directory
    """
    if env_dir := os.environ.get("HF_PROVIDER_SCRIPTDIR"):
        return Path(env_dir)
    
    return get_config_location().parent / "scripts"