"""onaws integration test configuration."""

import sys
from pathlib import Path

# Ensure repo root is on sys.path so hfmock.py and other root-level modules are importable
repo_root = Path(__file__).parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Ensure logs/ directory exists before any test module is imported
# (some test files create FileHandlers at module level)
logs_dir = repo_root / "logs"
logs_dir.mkdir(exist_ok=True)
