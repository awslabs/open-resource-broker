# Package Testing Strategy Implementation Plan

## Analysis Summary

Based on analysis of the codebase, the Open Resource Broker has optional dependencies defined in `pyproject.toml`:

- **cli**: `rich>=13.3.0`, `rich-argparse>=1.0.0`
- **api**: `fastapi>=0.104.0`, `uvicorn>=0.24.0`, `jinja2>=3.1.0`
- **monitoring**: `opentelemetry-*`, `prometheus-client>=0.17.0`, `psutil>=5.9.0`
- **all**: Includes all optional features

## Current State

### Good Import Guards Found
- `src/cli/main.py` - Has Rich import guard
- `src/cli/console.py` - Has Rich import guard with fallback
- `src/api/server.py` - Has FastAPI import guard

### Missing Import Guards
- `src/cli/formatters.py` - Uses Rich without proper guard
- `src/monitoring/health.py` - May use optional monitoring deps
- Various API modules - Need FastAPI guards
- Interface modules - Need optional dependency guards

## Implementation Plan

### 1. New CI Workflow: Package Variant Testing

Create `.github/workflows/package-testing.yml`:

```yaml
name: Package Testing Strategy

on:
  push:
    branches: [main]
    paths:
      - 'src/**'
      - 'pyproject.toml'
      - '.github/workflows/package-testing.yml'
  pull_request:
    branches: [main]
    paths:
      - 'src/**'
      - 'pyproject.toml'

jobs:
  package-variants:
    name: Test Package Variants
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        variant:
          - name: "minimal"
            install: "orb-py"
            description: "Core functionality only"
          - name: "cli"
            install: "orb-py[cli]"
            description: "CLI with rich formatting"
          - name: "api"
            install: "orb-py[api]"
            description: "API server functionality"
          - name: "monitoring"
            install: "orb-py[monitoring]"
            description: "Monitoring and observability"
          - name: "all"
            install: "orb-py[all]"
            description: "All features"
        python-version: ["3.10", "3.12"]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install package variant
        run: |
          python -m pip install --upgrade pip
          pip install build
          python -m build
          pip install dist/*.whl
          # Install specific variant
          pip install "${{ matrix.variant.install }}"

      - name: Test import guards
        run: |
          python -c "
          import sys
          print(f'Testing variant: ${{ matrix.variant.name }}')
          print(f'Python version: {sys.version}')
          
          # Test core imports always work
          try:
              import run
              from bootstrap import Application
              print('✓ Core imports successful')
          except ImportError as e:
              print(f'✗ Core import failed: {e}')
              sys.exit(1)
          
          # Test CLI functionality
          try:
              from cli.main import parse_args
              print('✓ CLI imports successful')
          except ImportError as e:
              print(f'✗ CLI import failed: {e}')
              if '${{ matrix.variant.name }}' in ['cli', 'all']:
                  sys.exit(1)
          
          # Test API functionality
          try:
              from api.server import create_fastapi_app
              print('✓ API imports successful')
          except ImportError as e:
              print(f'✗ API import failed: {e}')
              if '${{ matrix.variant.name }}' in ['api', 'all']:
                  sys.exit(1)
          
          print('All import tests passed!')
          "

      - name: Test CLI functionality
        run: |
          # Test basic CLI works
          orb --help
          orb --version
          
          # Test commands that should work in all variants
          orb templates list --help || true
          orb requests --help || true

      - name: Test API functionality (if available)
        if: contains(fromJSON('["api", "all"]'), matrix.variant.name)
        run: |
          python -c "
          from api.server import create_fastapi_app
          from config.config_manager import ConfigurationManager
          
          config = ConfigurationManager()
          app = create_fastapi_app(config.get_server_config())
          print('✓ FastAPI app creation successful')
          "

      - name: Test monitoring functionality (if available)
        if: contains(fromJSON('["monitoring", "all"]'), matrix.variant.name)
        run: |
          python -c "
          try:
              from monitoring.health import HealthCheck
              print('✓ Monitoring imports successful')
          except ImportError as e:
              print(f'✗ Monitoring import failed: {e}')
              import sys
              sys.exit(1)
          "

  import-guard-tests:
    name: Import Guard Validation
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Install minimal dependencies
        run: |
          python -m pip install --upgrade pip
          pip install build pytest
          python -m build
          pip install dist/*.whl

      - name: Test import guards without optional deps
        run: |
          python -m pytest tests/test_import_guards.py -v

  dependency-isolation:
    name: Dependency Isolation Test
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.12"

      - name: Test clean environment
        run: |
          python -m pip install --upgrade pip
          pip install build
          python -m build
          pip install dist/*.whl
          
          # Verify no optional dependencies are installed
          python -c "
          import sys
          
          optional_deps = ['rich', 'fastapi', 'uvicorn', 'opentelemetry', 'prometheus_client']
          for dep in optional_deps:
              try:
                  __import__(dep)
                  print(f'WARNING: {dep} is available but should not be')
              except ImportError:
                  print(f'✓ {dep} correctly not available')
          
          # Test that core functionality still works
          import run
          from bootstrap import Application
          print('✓ Core functionality works without optional deps')
          "
```

### 2. Files Needing Import Guards

#### A. CLI Module Files

**src/cli/formatters.py** - Add Rich import guard:
```python
# At top of file, replace direct Rich import
try:
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Table = None

def format_generic_table(items: list[dict], title: str = "Items") -> str:
    if not items:
        return f"No {title.lower()} found."

    if RICH_AVAILABLE:
        return _format_rich_table(items, title)
    else:
        return _format_generic_ascii_table(items, title)

def _format_rich_table(items: list[dict], title: str) -> str:
    # Existing Rich implementation
    pass
```

#### B. API Module Files

**src/api/routers/*.py** - Add FastAPI guards:
```python
try:
    from fastapi import APIRouter, HTTPException
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = None

def create_router():
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI not installed. Install with: pip install orb-py[api]")
    # Router implementation
```

#### C. Monitoring Module Files

**src/monitoring/health.py** - Add monitoring guards:
```python
# Optional monitoring dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    from opentelemetry import trace
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False

class HealthCheck:
    def get_system_metrics(self):
        if PSUTIL_AVAILABLE:
            return self._get_psutil_metrics()
        else:
            return {"system": "metrics unavailable - install orb-py[monitoring]"}
```

#### D. Interface Module Files

**src/interface/serve_command_handler.py** - Add API guards:
```python
def handle_serve_command(args):
    try:
        from api.server import create_fastapi_app
    except ImportError:
        raise ImportError(
            "API server functionality not available. "
            "Install with: pip install orb-py[api]"
        )
    # Implementation
```

### 3. Import Guard Patterns

#### Pattern 1: Feature Availability Check
```python
try:
    from optional_package import SomeClass
    FEATURE_AVAILABLE = True
except ImportError:
    FEATURE_AVAILABLE = False
    SomeClass = None

def use_feature():
    if not FEATURE_AVAILABLE:
        raise ImportError("Feature requires: pip install orb-py[feature]")
    return SomeClass()
```

#### Pattern 2: Graceful Degradation
```python
try:
    from rich.console import Console
    console = Console()
except ImportError:
    class PlainConsole:
        def print(self, text, **kwargs):
            print(text)
    console = PlainConsole()
```

#### Pattern 3: Lazy Import with Error
```python
def api_function():
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError("API functionality requires: pip install orb-py[api]")
    return FastAPI()
```

### 4. Testing Approach for Each Package Variant

#### A. Minimal Package (`orb-py`)
- Test core CLI commands work
- Test basic template operations
- Test request/machine operations
- Verify no optional dependencies imported
- Test graceful degradation of enhanced features

#### B. CLI Package (`orb-py[cli]`)
- Test Rich formatting works
- Test colored output
- Test table formatting
- Test help formatting with rich-argparse

#### C. API Package (`orb-py[api]`)
- Test FastAPI app creation
- Test API endpoints
- Test OpenAPI documentation
- Test server startup

#### D. Monitoring Package (`orb-py[monitoring]`)
- Test metrics collection
- Test health checks
- Test OpenTelemetry integration
- Test Prometheus metrics

#### E. All Package (`orb-py[all]`)
- Test all features work together
- Test no conflicts between optional dependencies
- Test full functionality

### 5. New Test File: `tests/test_import_guards.py`

```python
"""Test import guards for optional dependencies."""

import sys
import subprocess
from unittest.mock import patch
import pytest

class TestImportGuards:
    """Test that import guards work correctly."""

    def test_cli_without_rich(self):
        """Test CLI works without Rich installed."""
        with patch.dict(sys.modules, {'rich': None, 'rich.console': None}):
            from cli.console import get_console, print_success
            console = get_console()
            assert console is not None
            print_success("test")  # Should not raise

    def test_api_without_fastapi(self):
        """Test API gracefully fails without FastAPI."""
        with patch.dict(sys.modules, {'fastapi': None}):
            from api.server import create_fastapi_app
            with pytest.raises(ImportError, match="FastAPI not installed"):
                create_fastapi_app({})

    def test_monitoring_without_optional_deps(self):
        """Test monitoring works without optional dependencies."""
        with patch.dict(sys.modules, {'psutil': None, 'prometheus_client': None}):
            from monitoring.health import HealthCheck
            # Should create but with limited functionality
            health = HealthCheck(config=None)
            assert health is not None

    def test_core_imports_always_work(self):
        """Test core imports work regardless of optional dependencies."""
        # These should never fail
        from bootstrap import Application
        from domain.base.exceptions import DomainException
        from infrastructure.logging.logger import get_logger
        
        assert Application is not None
        assert DomainException is not None
        assert get_logger is not None

class TestPackageVariants:
    """Test different package installation variants."""

    @pytest.mark.integration
    def test_minimal_package_functionality(self):
        """Test minimal package provides core functionality."""
        # This would be run in CI with minimal install
        result = subprocess.run([
            sys.executable, "-c", 
            "import run; from bootstrap import Application; print('OK')"
        ], capture_output=True, text=True)
        assert result.returncode == 0
        assert "OK" in result.stdout

    @pytest.mark.integration  
    def test_cli_package_functionality(self):
        """Test CLI package provides enhanced formatting."""
        # This would be run in CI with CLI install
        result = subprocess.run([
            sys.executable, "-c",
            "from cli.formatters import format_generic_table; print('OK')"
        ], capture_output=True, text=True)
        assert result.returncode == 0

class TestErrorMessages:
    """Test that error messages are helpful."""

    def test_api_error_message_helpful(self):
        """Test API error message tells user how to install."""
        with patch.dict(sys.modules, {'fastapi': None}):
            from api.server import create_fastapi_app
            with pytest.raises(ImportError) as exc_info:
                create_fastapi_app({})
            
            error_msg = str(exc_info.value)
            assert "pip install orb-py[api]" in error_msg

    def test_monitoring_error_message_helpful(self):
        """Test monitoring error message is helpful."""
        with patch.dict(sys.modules, {'prometheus_client': None}):
            # Test would check that error messages guide user to correct install
            pass
```

### 6. Implementation Priority

1. **High Priority** (Breaks basic functionality):
   - `src/cli/formatters.py` - Rich import guard
   - `src/api/server.py` - Verify FastAPI guard is complete
   - `src/interface/serve_command_handler.py` - API guard

2. **Medium Priority** (Enhances user experience):
   - All API router files - FastAPI guards
   - Monitoring modules - Optional dependency guards
   - Better error messages

3. **Low Priority** (Nice to have):
   - Enhanced fallback implementations
   - More detailed feature detection

### 7. Validation Strategy

1. **Automated Testing**: CI workflow tests all variants
2. **Manual Testing**: Local testing with different installs
3. **Documentation**: Update README with installation options
4. **Error Handling**: Ensure helpful error messages

This implementation ensures the package works correctly across all installation variants while providing clear guidance to users about which features require which optional dependencies.