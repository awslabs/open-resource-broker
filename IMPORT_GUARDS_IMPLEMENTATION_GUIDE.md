# Import Guards Implementation Guide

## Files Requiring Import Guards

### 1. CLI Module Files (Rich Dependencies)

#### `src/cli/formatters.py` - NEEDS IMPLEMENTATION
**Current Issue**: Uses Rich directly without guard
**Required Changes**:
```python
# At top of file, add:
try:
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Table = None

def format_generic_table(items: list[dict], title: str = "Items") -> str:
    """Format any list of dictionaries as a table - pure dynamic, no hardcoding."""
    if not items:
        return f"No {title.lower()} found."

    if RICH_AVAILABLE:
        return _format_rich_table(items, title)
    else:
        return _format_generic_ascii_table(items, title)

def _format_rich_table(items: list[dict], title: str) -> str:
    """Format using Rich (existing implementation)."""
    from cli.console import get_console
    
    # Get all unique keys from all items
    all_keys = set()
    for item in items:
        all_keys.update(item.keys())

    # Create table with dynamic columns
    table = Table(show_header=True, header_style="bold magenta", show_lines=True, title=title)
    for key in sorted(all_keys):
        header = key.replace("_", " ").replace("Id", " ID").title()
        table.add_column(header)

    # Add rows with all data
    for item in items:
        row = [str(item.get(key, "N/A")) for key in sorted(all_keys)]
        table.add_row(*row)

    # Capture output using shared console
    console = get_console()
    with console.capture() as capture:
        console.print(table)
    return capture.get()
```

#### `src/cli/main.py` - ALREADY HAS GUARD ✓
**Status**: Already implemented correctly
```python
try:
    from rich_argparse import RichHelpFormatter
    HELP_FORMATTER = RichHelpFormatter
except ImportError:
    HELP_FORMATTER = argparse.RawDescriptionHelpFormatter
```

#### `src/cli/console.py` - ALREADY HAS GUARD ✓
**Status**: Already implemented correctly with fallback classes

### 2. API Module Files (FastAPI Dependencies)

#### `src/api/server.py` - ALREADY HAS GUARD ✓
**Status**: Already implemented correctly
```python
try:
    from fastapi import FastAPI, Request
    # ... other FastAPI imports
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
```

#### `src/api/routers/machines.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
try:
    from fastapi import APIRouter, HTTPException, Depends
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = None
    HTTPException = None
    Depends = None
    JSONResponse = None

def create_machines_router():
    """Create machines router."""
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not installed. API functionality requires FastAPI.\n"
            "Install with: pip install orb-py[api]"
        )
    
    router = APIRouter(prefix="/machines", tags=["machines"])
    # ... router implementation
    return router
```

#### `src/api/routers/templates.py` - NEEDS IMPLEMENTATION
**Required Changes**: Same pattern as machines.py

#### `src/api/routers/requests.py` - NEEDS IMPLEMENTATION
**Required Changes**: Same pattern as machines.py

#### `src/api/middleware/logging_middleware.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
try:
    from fastapi import Request, Response
    from fastapi.middleware.base import BaseHTTPMiddleware
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    Request = None
    Response = None
    BaseHTTPMiddleware = None

class LoggingMiddleware:
    def __init__(self):
        if not FASTAPI_AVAILABLE:
            raise ImportError(
                "FastAPI not installed. Middleware requires FastAPI.\n"
                "Install with: pip install orb-py[api]"
            )
```

#### `src/api/middleware/auth_middleware.py` - NEEDS IMPLEMENTATION
**Required Changes**: Same pattern as logging_middleware.py

#### `src/api/documentation/openapi_config.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
try:
    from fastapi import FastAPI
    from fastapi.openapi.utils import get_openapi
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = None
    get_openapi = None

def configure_openapi(app):
    if not FASTAPI_AVAILABLE:
        raise ImportError(
            "FastAPI not installed. OpenAPI configuration requires FastAPI.\n"
            "Install with: pip install orb-py[api]"
        )
```

### 3. Interface Module Files

#### `src/interface/serve_command_handler.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
def handle_serve_command(args):
    """Handle serve command."""
    try:
        from api.server import create_fastapi_app
        import uvicorn
    except ImportError as e:
        if "FastAPI" in str(e):
            raise ImportError(
                "API server functionality not available. FastAPI not installed.\n"
                "Install with: pip install orb-py[api]"
            ) from e
        elif "uvicorn" in str(e):
            raise ImportError(
                "ASGI server not available. Uvicorn not installed.\n"
                "Install with: pip install orb-py[api]"
            ) from e
        else:
            raise
    
    # Implementation continues...
```

### 4. Monitoring Module Files

#### `src/monitoring/health.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
# Optional monitoring dependencies
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    from prometheus_client import Counter, Histogram, Gauge
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    Counter = None
    Histogram = None
    Gauge = None

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False
    trace = None
    Status = None
    StatusCode = None

class HealthCheck:
    def get_system_metrics(self):
        """Get system metrics if psutil is available."""
        if PSUTIL_AVAILABLE:
            return {
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent
            }
        else:
            return {
                "system": "System metrics unavailable - install orb-py[monitoring] for detailed metrics"
            }
    
    def get_prometheus_metrics(self):
        """Get Prometheus metrics if available."""
        if PROMETHEUS_AVAILABLE:
            # Return actual metrics
            pass
        else:
            return {"prometheus": "Prometheus metrics unavailable - install orb-py[monitoring]"}
```

#### `src/monitoring/metrics.py` - NEEDS REVIEW
**Current Status**: Appears to not use optional dependencies directly, but should be reviewed

### 5. Infrastructure Module Files

#### `src/infrastructure/di/server_services.py` - NEEDS IMPLEMENTATION
**Required Changes**:
```python
def register_api_services(container):
    """Register API-related services."""
    try:
        from api.server import create_fastapi_app
        # Register API services
    except ImportError:
        # Skip API service registration if FastAPI not available
        logger.info("FastAPI not available, skipping API service registration")
        return
```

## Import Guard Patterns

### Pattern 1: Availability Flag with Error
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

### Pattern 2: Graceful Degradation
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

### Pattern 3: Lazy Import with Error
```python
def api_function():
    try:
        from fastapi import FastAPI
    except ImportError:
        raise ImportError("API functionality requires: pip install orb-py[api]")
    return FastAPI()
```

### Pattern 4: Optional Feature Detection
```python
def get_available_features():
    features = {}
    
    try:
        import rich
        features['rich_formatting'] = True
    except ImportError:
        features['rich_formatting'] = False
    
    return features
```

## Testing Strategy

### 1. Unit Tests for Import Guards
- Test each module with mocked missing dependencies
- Verify graceful degradation
- Verify helpful error messages

### 2. Integration Tests for Package Variants
- Test minimal install works
- Test each optional feature install works
- Test all features install works

### 3. CI Workflow Testing
- Test all package variants in CI
- Test import guards work correctly
- Test error messages are helpful

## Implementation Priority

### High Priority (Breaks functionality)
1. `src/cli/formatters.py` - Rich import guard
2. `src/api/routers/*.py` - FastAPI import guards
3. `src/interface/serve_command_handler.py` - API server guard

### Medium Priority (User experience)
1. `src/api/middleware/*.py` - FastAPI middleware guards
2. `src/monitoring/health.py` - Optional monitoring guards
3. `src/infrastructure/di/server_services.py` - Service registration guards

### Low Priority (Nice to have)
1. Enhanced error messages
2. Feature detection utilities
3. Better fallback implementations

## Validation Checklist

- [ ] All files with optional imports have guards
- [ ] Error messages include installation instructions
- [ ] Graceful degradation where possible
- [ ] Core functionality works without optional deps
- [ ] CI tests all package variants
- [ ] Import guard tests pass
- [ ] Documentation updated with installation options