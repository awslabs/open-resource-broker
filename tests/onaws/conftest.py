"""onaws integration test configuration."""

import sys
from pathlib import Path

import pytest

# Ensure repo root is on sys.path so hfmock.py and other root-level modules are importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Ensure logs/ directory exists before any test module is imported
# (some test files create FileHandlers at module level)
logs_dir = repo_root / "logs"
logs_dir.mkdir(exist_ok=True)


@pytest.fixture(autouse=True)
def reset_di_container():
    """Reset DI container between tests.

    Each onaws test sets ORB_CONFIG_DIR to a per-test temp directory.
    ConfigurationManager is a DI singleton that caches the config path at
    construction time. Without a reset, the second test's container still
    reads/writes to the first test's work directory.
    """
    yield
    from infrastructure.di.container import reset_container

    reset_container()
