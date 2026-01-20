"""
Open Resource Broker - Main package namespace.

This package provides a clean, namespaced API for the Open Resource Broker,
allowing users to import from orb_py.sdk, orb_py.mcp, etc.

Example:
    from orb_py import orb
    from orb_py.sdk import OpenResourceBroker
    from orb_py.mcp import OpenResourceBrokerMCPTools

    async with orb(provider="aws") as client:
        templates = await client.list_templates()
"""

import sys
from pathlib import Path

# Re-export main SDK components at package level
from sdk import (
    OpenResourceBroker,
    ORB,
    orb,
    SDKConfig,
    SDKError,
    ConfigurationError,
    ProviderError,
)

# Re-export MCP components
from mcp import (
    OpenResourceBrokerMCPTools,
    MCPToolDiscovery,
)

# Auto-discover and register all top-level packages as submodules
# This allows: from orb_py.sdk import ..., from orb_py.mcp import ..., etc.
_src_dir = Path(__file__).parent.parent

# Find all directories in src/ that are Python packages (have __init__.py)
for _path in _src_dir.iterdir():
    if _path.is_dir() and not _path.name.startswith(("_", ".")):
        # Check if it's a Python package
        if (_path / "__init__.py").exists() or any(_path.glob("*.py")):
            _module_name = _path.name
            # Skip orb_py itself to avoid circular reference
            if _module_name == "orb_py":
                continue
            try:
                _module = __import__(_module_name)
                sys.modules[f"orb_py.{_module_name}"] = _module
            except ImportError:
                # Module can't be imported, skip it
                pass

__all__ = [
    # Main SDK exports (recommended for users)
    "OpenResourceBroker",
    "ORB",
    "orb",
    "SDKConfig",
    "SDKError",
    "ConfigurationError",
    "ProviderError",
    # MCP exports
    "OpenResourceBrokerMCPTools",
    "MCPToolDiscovery",
]

__version__ = "1.0.0"
