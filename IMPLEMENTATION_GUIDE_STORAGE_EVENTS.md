# Implementation Guide: Storage Events Migration

## Overview
This guide provides step-by-step instructions to migrate infrastructure events from the domain layer to the infrastructure layer.

---

## Pre-Migration Checklist

### 1. Find All Usages
```bash
# Find all files importing storage events
grep -r "from domain.base.events import.*Storage" src/
grep -r "from domain.base.events import.*Repository" src/
grep -r "from domain.base.events import.*Transaction" src/
grep -r "from.*storage_events import" src/

# Find all files using these event classes
grep -r "RepositoryOperationStartedEvent\|RepositoryOperationCompletedEvent\|RepositoryOperationFailedEvent" src/
grep -r "TransactionStartedEvent\|TransactionCommittedEvent" src/
grep -r "StorageStrategySelectedEvent\|StorageStrategyFailoverEvent" src/
grep -r "ConnectionPoolEvent\|StorageHealthCheckEvent" src/
```

### 2. Run Baseline Tests
```bash
# Ensure all tests pass before migration
pytest tests/ -v
```

---

## Migration Steps

### Step 1: Create Infrastructure Events Module

**File**: `src/infrastructure/events/storage_events.py`

```python
"""Infrastructure storage events - Repository and storage monitoring.

These events track infrastructure-level storage operations, performance,
and health. They are NOT domain business events - they are technical
telemetry for monitoring, debugging, and observability.

Domain events (business-significant state changes) live in domain/base/events/.
"""

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import Field

from domain.base.events import (
    ErrorEvent,
    InfrastructureEvent,
    OperationEvent,
    PerformanceEvent,
    TimedEvent,
)

# =============================================================================
# REPOSITORY OPERATION EVENTS
# =============================================================================


class StorageEvent(InfrastructureEvent):
    """Base class for storage-related infrastructure events."""

    operation_id: str
    entity_type: str
    entity_id: str
    storage_strategy: str


class RepositoryOperationStartedEvent(StorageEvent):
    """Infrastructure event: repository operation started.
    
    Tracks when a database/storage operation begins for performance monitoring.
    This is NOT a domain event - business logic should not depend on this.
    """

    operation_type: str  # "save", "find", "delete", "update"
    start_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RepositoryOperationCompletedEvent(StorageEvent, OperationEvent):
    """Infrastructure event: repository operation completed successfully.
    
    Tracks successful completion of storage operations for monitoring.
    """

    records_affected: int = 1


class RepositoryOperationFailedEvent(StorageEvent, ErrorEvent, TimedEvent):
    """Infrastructure event: repository operation failed.
    
    Tracks storage operation failures for debugging and alerting.
    """

    operation_type: str
    duration_ms: Optional[float] = None


class SlowQueryDetectedEvent(StorageEvent, PerformanceEvent):
    """Infrastructure event: slow storage operation detected.
    
    Triggers when a storage operation exceeds performance thresholds.
    Used for performance monitoring and optimization.
    """

    operation_type: str
    query_details: dict[str, Any] = Field(default_factory=dict)


class TransactionStartedEvent(InfrastructureEvent):
    """Infrastructure event: database transaction started.
    
    Tracks transaction lifecycle for debugging and monitoring.
    """

    transaction_id: str
    isolation_level: str = "default"
    entities_involved: list[str] = Field(default_factory=list)


class TransactionCommittedEvent(InfrastructureEvent, TimedEvent):
    """Infrastructure event: database transaction committed.
    
    Tracks successful transaction completion.
    """

    transaction_id: str
    entities_affected: list[str] = Field(default_factory=list)
    operations_count: int


# =============================================================================
# STORAGE STRATEGY EVENTS
# =============================================================================


class StorageStrategyEvent(InfrastructureEvent):
    """Base class for storage strategy infrastructure events."""

    strategy_type: str
    entity_type: str


class StorageStrategySelectedEvent(StorageStrategyEvent):
    """Infrastructure event: storage strategy selected.
    
    Tracks which storage backend (JSON/SQL/DynamoDB) was chosen.
    """

    selected_strategy: str  # "JSON", "SQL", "DynamoDB"
    selection_reason: str  # "configuration", "fallback", "performance"
    available_strategies: list[str] = Field(default_factory=list)


class StorageStrategyFailoverEvent(StorageStrategyEvent, ErrorEvent):
    """Infrastructure event: storage strategy failover occurred.
    
    Tracks when system fails over from one storage backend to another.
    Critical for reliability monitoring.
    """

    from_strategy: str
    to_strategy: str
    failure_reason: str
    failover_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConnectionPoolEvent(InfrastructureEvent):
    """Infrastructure event: connection pool operation.
    
    Tracks connection pool health and resource utilization.
    """

    pool_type: str  # "SQL", "DynamoDB", "Redis"
    event_type: str  # "connection_acquired", "connection_released", "pool_exhausted"
    active_connections: int
    pool_size: int
    wait_time_ms: Optional[float] = None


class StoragePerformanceEvent(StorageStrategyEvent, PerformanceEvent):
    """Infrastructure event: storage performance metrics.
    
    Tracks storage throughput and performance characteristics.
    """

    operation_type: str
    data_size_bytes: int
    throughput_ops_per_sec: Optional[float] = None


class StorageHealthCheckEvent(StorageStrategyEvent, PerformanceEvent):
    """Infrastructure event: storage health check result.
    
    Tracks storage backend health status for monitoring.
    """

    health_status: str  # "healthy", "degraded", "unhealthy"
    response_time_ms: float
    error_rate_percent: float
    check_details: dict[str, Any] = Field(default_factory=dict)
```

**File**: `src/infrastructure/events/__init__.py`

```python
"""Infrastructure events - Technical monitoring and observability events.

These events track infrastructure-level operations, performance, and health.
They are separate from domain business events.
"""

from .storage_events import (
    ConnectionPoolEvent,
    RepositoryOperationCompletedEvent,
    RepositoryOperationFailedEvent,
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
    StorageEvent,
    StorageHealthCheckEvent,
    StoragePerformanceEvent,
    StorageStrategyEvent,
    StorageStrategyFailoverEvent,
    StorageStrategySelectedEvent,
    TransactionCommittedEvent,
    TransactionStartedEvent,
)

__all__ = [
    "ConnectionPoolEvent",
    "RepositoryOperationCompletedEvent",
    "RepositoryOperationFailedEvent",
    "RepositoryOperationStartedEvent",
    "SlowQueryDetectedEvent",
    "StorageEvent",
    "StorageHealthCheckEvent",
    "StoragePerformanceEvent",
    "StorageStrategyEvent",
    "StorageStrategyFailoverEvent",
    "StorageStrategySelectedEvent",
    "TransactionCommittedEvent",
    "TransactionStartedEvent",
]
```

### Step 2: Update Repository Imports

**File**: `src/infrastructure/storage/repositories/request_repository.py`

```python
# OLD IMPORTS (lines 8-14)
from domain.base.events import (
    DomainEvent,
    RepositoryOperationCompletedEvent,
    RepositoryOperationFailedEvent,
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
)

# NEW IMPORTS
from domain.base.events import DomainEvent
from infrastructure.events.storage_events import (
    RepositoryOperationCompletedEvent,
    RepositoryOperationFailedEvent,
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
)
```

### Step 3: Update Domain Events Module

**File**: `src/domain/base/events/__init__.py`

Remove storage event imports and exports:

```python
# REMOVE these lines (59-73):
# Storage events (Repository and storage)
from .storage_events import (
    ConnectionPoolEvent,
    RepositoryOperationCompletedEvent,
    RepositoryOperationFailedEvent,
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
    StorageEvent,
    StorageHealthCheckEvent,
    StoragePerformanceEvent,
    StorageStrategyEvent,
    StorageStrategyFailoverEvent,
    StorageStrategySelectedEvent,
    TransactionCommittedEvent,
    TransactionStartedEvent,
)

# REMOVE from __all__ list (lines 101, 122-123, 131-133, 148, 151-155, 165-166):
"ConnectionPoolEvent",
"StorageEvent",
"StorageStrategyEvent",
"RepositoryOperationCompletedEvent",
"RepositoryOperationFailedEvent",
"RepositoryOperationStartedEvent",
"SlowQueryDetectedEvent",
"StorageEvent",
"StorageHealthCheckEvent",
"StoragePerformanceEvent",
"StorageStrategyFailoverEvent",
"StorageStrategySelectedEvent",
"TransactionCommittedEvent",
"TransactionStartedEvent",
```

### Step 4: Delete or Repurpose Domain Storage Events File

**Option A: Delete the file**
```bash
rm src/domain/base/events/storage_events.py
```

**Option B: Repurpose for true domain persistence events**

Keep the file but replace content with domain-level persistence events:

```python
"""Domain persistence events - Business-significant storage state changes.

These events represent business-level concerns about data persistence,
NOT infrastructure monitoring. They describe what happened to business
entities from a domain perspective.
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import Field

from .base_events import DomainEvent, ErrorEvent


class EntityPersistenceFailedEvent(DomainEvent, ErrorEvent):
    """Domain event: entity could not be persisted.
    
    Raised when a business entity (Request, Machine, Template) cannot
    be saved, indicating a business-level failure that may require
    compensating actions or user notification.
    """

    entity_type: str  # "Request", "Machine", "Template"
    entity_id: str
    failure_reason: str  # Business-level reason: "validation_failed", "storage_unavailable"
    retry_possible: bool = True


class EntityRestoredEvent(DomainEvent):
    """Domain event: entity was restored from persistent storage.
    
    Raised when a previously persisted entity is successfully loaded,
    useful for audit trails and recovery scenarios.
    """

    entity_type: str
    entity_id: str
    restored_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "persistent_storage"  # vs "cache", "backup"


# Note: Most domain logic doesn't need explicit persistence events.
# The domain should be persistence-ignorant. Only add events here if
# business logic needs to react to persistence state changes.
```

### Step 5: Update Tests

Find and update test files:

```bash
# Find test files using storage events
grep -r "RepositoryOperationStartedEvent\|StorageStrategySelectedEvent" tests/

# Update imports in test files
# OLD:
from domain.base.events import RepositoryOperationStartedEvent

# NEW:
from infrastructure.events.storage_events import RepositoryOperationStartedEvent
```

### Step 6: Verify Migration

```bash
# Check for any remaining imports from domain
grep -r "from domain.base.events import.*Storage" src/
grep -r "from domain.base.events import.*Repository" src/
grep -r "from domain.base.events import.*Transaction" src/

# Should return no results (or only the new domain persistence events)

# Run tests
pytest tests/ -v

# Check for import errors
python -m py_compile src/infrastructure/events/storage_events.py
python -m py_compile src/infrastructure/storage/repositories/request_repository.py
```

---

## Post-Migration Tasks

### 1. Update Documentation

**File**: `src/domain/README.md`

Add section:

```markdown
## Domain Events vs Infrastructure Events

### Domain Events (in domain/base/events/)
Events that represent business-significant state changes:
- RequestCreatedEvent - A new request was submitted
- MachineProvisionedEvent - A machine became available
- TemplateValidatedEvent - A template passed validation

These events use business terminology and trigger business workflows.

### Infrastructure Events (in infrastructure/events/)
Events that track technical operations and monitoring:
- RepositoryOperationCompletedEvent - Database operation finished
- StorageStrategyFailoverEvent - Storage backend switched
- SlowQueryDetectedEvent - Performance threshold exceeded

These events use technical terminology and support observability.

### The Test
"Would a business analyst care about this event?"
- Yes → Domain event
- No → Infrastructure event
```

**File**: `src/infrastructure/README.md`

Add section:

```markdown
## Infrastructure Events

Infrastructure events track technical operations, performance, and health.
They live in `infrastructure/events/` and are separate from domain business events.

### Storage Events
Located in `infrastructure/events/storage_events.py`:
- Repository operation lifecycle (started, completed, failed)
- Transaction tracking
- Storage strategy selection and failover
- Connection pool monitoring
- Performance metrics and health checks

### Usage
```python
from infrastructure.events.storage_events import (
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
)

# Emit infrastructure event for monitoring
event = RepositoryOperationStartedEvent(
    aggregate_id=operation_id,
    aggregate_type="RepositoryOperation",
    operation_id=operation_id,
    entity_type="Request",
    entity_id=request_id,
    storage_strategy="SQL",
    operation_type="save",
)
event_publisher.publish(event)
```

These events are consumed by monitoring systems, not business logic.
```

### 2. Update Architecture Decision Record

Create `docs/adr/ADR-XXX-separate-domain-infrastructure-events.md`:

```markdown
# ADR-XXX: Separate Domain and Infrastructure Events

## Status
Accepted

## Context
Storage events were originally placed in `domain/base/events/storage_events.py`,
mixing business domain events with infrastructure monitoring events. This violated
Domain-Driven Design principles and made the domain layer harder to understand.

## Decision
We will separate events into two categories:

1. **Domain Events** (in `domain/base/events/`): Business-significant state changes
2. **Infrastructure Events** (in `infrastructure/events/`): Technical monitoring

Storage monitoring events (repository operations, transactions, connection pools,
performance metrics) are infrastructure concerns and belong in the infrastructure layer.

## Consequences

### Positive
- Clear separation of business and technical concerns
- Domain layer is easier to understand for business stakeholders
- Infrastructure events can evolve independently
- Better alignment with DDD principles

### Negative
- Import paths change for existing code
- Need to update documentation and examples
- Developers must understand the distinction

### Neutral
- Event publishing infrastructure remains unchanged
- Both event types still inherit from DomainEvent base class
- No runtime behavior changes

## Implementation
- Created `infrastructure/events/storage_events.py`
- Moved 13 infrastructure events from domain layer
- Updated imports in repository implementations
- Added documentation explaining the distinction
```

---

## Rollback Plan

If issues arise during migration:

```bash
# 1. Revert the changes
git revert <commit-hash>

# 2. Or manually restore
git checkout HEAD~1 -- src/domain/base/events/storage_events.py
git checkout HEAD~1 -- src/domain/base/events/__init__.py
git checkout HEAD~1 -- src/infrastructure/storage/repositories/request_repository.py

# 3. Delete new infrastructure events
rm -rf src/infrastructure/events/storage_events.py

# 4. Run tests
pytest tests/ -v
```

---

## Validation Checklist

- [ ] All storage events moved to `infrastructure/events/storage_events.py`
- [ ] Domain events module cleaned up
- [ ] Repository imports updated
- [ ] Test imports updated
- [ ] All tests pass
- [ ] No import errors
- [ ] Documentation updated
- [ ] ADR created
- [ ] Code review completed
- [ ] Changes committed

---

## Timeline

- **Step 1-2**: 30 minutes (create infrastructure events, update imports)
- **Step 3-4**: 15 minutes (clean up domain events)
- **Step 5**: 30 minutes (update tests)
- **Step 6**: 15 minutes (verification)
- **Post-migration**: 30 minutes (documentation)

**Total**: ~2 hours

---

## Questions & Answers

**Q: Why keep InfrastructureEvent inheriting from DomainEvent?**
A: The event publisher needs a common interface. Infrastructure events are still "events", just not business events. The inheritance hierarchy is correct; the file location was wrong.

**Q: Should we create domain persistence events?**
A: Only if business logic needs to react to persistence state changes. Most domain logic should be persistence-ignorant.

**Q: What about existing event handlers?**
A: They continue to work unchanged. The event publisher handles all event types uniformly.

**Q: How do we prevent this from happening again?**
A: Add linting rules, code review guidelines, and clear documentation about the distinction.
