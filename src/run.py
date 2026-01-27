#!/usr/bin/env python3
"""CLI entry point with resource-action structure."""

import asyncio
import os
import sys

# Add project root to Python path to enable absolute imports
# This allows src/run.py to import using src.module.submodule pattern
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level from src/ to project root
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Setup environment variables for config discovery
def setup_environment():
    """Setup environment variables using platform-specific directories."""
    # Only set if not already set by user
    if os.environ.get("HF_PROVIDER_CONFDIR"):
        return  # User has explicitly set it
    
    try:
        from config.platform_dirs import get_config_location, get_work_location, get_logs_location
        
        config_dir = str(get_config_location())
        work_dir = str(get_work_location())
        logs_dir = str(get_logs_location())
        
        os.environ.setdefault("HF_PROVIDER_CONFDIR", config_dir)
        os.environ.setdefault("HF_PROVIDER_WORKDIR", work_dir)
        os.environ.setdefault("HF_PROVIDER_LOGDIR", logs_dir)
        os.environ.setdefault("DEFAULT_PROVIDER_CONFDIR", config_dir)
        os.environ.setdefault("DEFAULT_PROVIDER_WORKDIR", work_dir)
        
    except Exception as e:
        # Config discovery failed - will be caught later with helpful error
        print(f"WARNING: Config directory detection failed: {e}", file=sys.stderr)

# Setup environment
setup_environment()

# Import CLI modules
try:
    # Try wheel/installed package import first
    from cli.main import main
except ImportError:
    # Fallback to development mode import
    from cli.main import main

# Import version for help text
try:
    from ._package import __version__
except ImportError:
    # Fallback for direct execution
    __version__ = "0.1.0"


def cli_main() -> None:
    """Entry point function for console scripts."""
    return asyncio.run(main())


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
    
    asyncio.run(main())
