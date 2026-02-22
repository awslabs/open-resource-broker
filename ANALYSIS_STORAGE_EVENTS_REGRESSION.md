# Regression Analysis: Domain Events Infrastructure Leak

## Executive Summary

**Problem**: The file `src/domain/base/events/storage_events.py` contains 13 event classes that mix pure domain business logic with infrastructure monitoring concerns, violating Domain-Driven Design principles and creating architectural debt.

**Impact**: Medium-High
- Domain layer polluted with infrastructure details
- Breaks separation of concerns
- Confuses business events with technical telemetry
- Makes domain harder to understand and maintain

**Recommendation**: Split events into domain and infrastructure layers, moving 11 of 13 events to infrastructure.

---

## 1. Event Classification Analysis

### Pure Infrastructure Events (11 events - MOVE to infrastructure)

These events are **technical telemetry** that a business analyst would never care about:

#### Repository Operation Events (4 events)
- `RepositoryOperationStartedEvent` - Database operation timing
- `RepositoryOperationCompletedEvent` - Database operation success metrics
- `RepositoryOperationFailedEvent` - Database operation failures
- `SlowQueryDetectedEvent` - Performance monitoring

**Why Infrastructure**: These track database/storage layer performance. Business doesn't care about "slow queries" or "repository operations" - they care about requests completing or failing.

#### Transaction Events (2 events)
- `TransactionStartedEvent` - Database transaction lifecycle
- `TransactionCommittedEvent` - Database transaction completion

**Why Infrastructure**: Transactions are a technical implementation detail. Business thinks in terms of "request submitted" or "machine created", not "transaction committed".

#### Storage Strategy Events (3 events)
- `StorageStrategySelectedEvent` - Which storage backend was chosen (JSON/SQL/DynamoDB)
- `StorageStrategyFailoverEvent` - Storage backend failover
- `StoragePerformanceEvent` - Storage throughput metrics

**Why Infrastructure**: Storage strategy is a technical decision. Business doesn't care if data is in JSON files or DynamoDB.

#### Connection & Health Events (2 events)
- `ConnectionPoolEvent` - Connection pool exhaustion, wait times
- `StorageHealthCheckEvent` - Storage backend health monitoring

**Why Infrastructure**: Pure operational monitoring. Business doesn't care about connection pools.

### Base Classes (2 events - KEEP in domain, but rename/clarify)

- `StorageEvent` - Currently used as base for infrastructure events
- `StorageStrategyEvent` - Currently used as base for infrastructure events

**Decision**: These are actually infrastructure base classes. They should move to infrastructure OR be removed entirely if we create proper infrastructure event base classes.

---

## 2. What's Missing: True Domain Events

The domain layer should have events that represent **business-significant state changes**:

### What Business Cares About:

```python
# Domain events that SHOULD exist (examples):
class RequestDataPersisted(DomainEvent):
    """Request was successfully saved - business cares about this."""
    request_id: str
    persistence_strategy: str  # "durable" vs "ephemeral" - business concept

class RequestDataLost(DomainEvent):
    """Request data could not be persisted - business failure."""
    request_id: str
    reason: str  # "storage_unavailable", "validation_failed"

class MachineStatePersisted(DomainEvent):
    """Machine state was successfully saved."""
    machine_id: str

class TemplateStorageFailure(DomainEvent):
    """Template could not be stored - business impact."""
    template_id: str
    reason: str
```

**Key Difference**: Domain events describe **what happened to business entities**, not how the infrastructure performed.

---

## 3. Architecture Decision

### Current State (WRONG):
```
domain/base/events/
├── storage_events.py  # Contains infrastructure monitoring events
└── domain_events.py   # Contains business events
```

### Target State (CORRECT):
```
domain/base/events/
└── domain_events.py   # Only business events

infrastructure/events/
├── storage_events.py  # Infrastructure monitoring events
└── monitoring_events.py  # Performance/health events
```

---

## 4. Detailed Migration Plan

### Phase 1: Create Infrastructure Events Module

**Action**: Create `src/infrastructure/events/storage_events.py`

**Contents**: Move all 11 infrastructure events + base classes

**Changes Required**:
1. Create new file with proper infrastructure event base class
2. Update imports in `infrastructure/storage/repositories/`
3. Update `domain/base/events/__init__.py` to remove these exports

### Phase 2: Update Event Inheritance

**Current Problem**: Infrastructure events inherit from `InfrastructureEvent(DomainEvent)`

**Decision**: Keep this pattern - `InfrastructureEvent` is correctly defined as a subtype of `DomainEvent` for event publishing infrastructure to work uniformly.

**Rationale**: The event publisher needs a common interface. Infrastructure events are still "events", just not domain business events.

### Phase 3: Update Imports

**Files to Update**:
- `src/infrastructure/storage/repositories/request_repository.py` (confirmed usage)
- `src/domain/base/events/__init__.py` (remove exports)
- Any other repository implementations

**Change**:
```python
# OLD
from domain.base.events import (
    RepositoryOperationStartedEvent,
    RepositoryOperationCompletedEvent,
    ...
)

# NEW
from infrastructure.events.storage_events import (
    RepositoryOperationStartedEvent,
    RepositoryOperationCompletedEvent,
    ...
)
```

### Phase 4: Add True Domain Events (Optional Enhancement)

If business logic needs to react to persistence events, add proper domain events:

```python
# In domain/base/events/domain_events.py
class EntityPersistenceFailedEvent(DomainEvent):
    """Domain entity could not be persisted - business impact."""
    entity_type: str  # "Request", "Machine", "Template"
    entity_id: str
    failure_reason: str  # Business-level reason
```

---

## 5. Implementation Steps

### Step 1: Create Infrastructure Events Module
```bash
mkdir -p src/infrastructure/events
touch src/infrastructure/events/__init__.py
touch src/infrastructure/events/storage_events.py
```

### Step 2: Move Event Definitions
- Copy all events from `domain/base/events/storage_events.py`
- Update imports to use `infrastructure` base classes
- Add proper module docstring

### Step 3: Update Domain Events Module
- Remove storage events from `domain/base/events/storage_events.py`
- Delete the file or repurpose for true domain persistence events
- Update `domain/base/events/__init__.py`

### Step 4: Update All Imports
- Search for all imports of storage events
- Update to import from `infrastructure.events.storage_events`
- Run tests to verify

### Step 5: Update Documentation
- Update `src/domain/README.md` to clarify domain events
- Update `src/infrastructure/README.md` to document infrastructure events
- Add examples of the distinction

---

## 6. Risk Assessment

### Low Risk:
- Events are only used for monitoring/logging
- No business logic depends on these events
- Event publisher handles all event types uniformly

### Medium Risk:
- Import changes across multiple files
- Need to update all repository implementations
- Potential for missed imports during migration

### Mitigation:
- Use grep to find all usages before migration
- Run full test suite after changes
- Update in single atomic commit

---

## 7. Success Metrics

### After Migration:
1. **Domain Purity**: `domain/base/events/` contains only business events
2. **Clear Separation**: Infrastructure events live in `infrastructure/events/`
3. **No Broken Imports**: All tests pass
4. **Better Clarity**: New developers can distinguish business from technical events

### Test Coverage:
- Verify event publishing still works
- Verify repository operations still emit events
- Verify event handlers receive events correctly

---

## 8. Alternative Approaches Considered

### Alternative 1: Keep Everything in Domain
**Rejected**: Violates DDD principles, pollutes domain with infrastructure concerns

### Alternative 2: Create Separate Event Types (InfrastructureEvent vs DomainEvent)
**Partially Adopted**: We already have `InfrastructureEvent` base class, but it's in the wrong location

### Alternative 3: Remove Infrastructure Events Entirely
**Rejected**: These events provide valuable monitoring and observability

---

## 9. Long-term Architectural Guidance

### Domain Events Should:
- Represent business-significant state changes
- Use business terminology (not technical terms)
- Be understandable by non-technical stakeholders
- Trigger business workflows and reactions

### Infrastructure Events Should:
- Monitor technical performance and health
- Track system-level operations
- Support observability and debugging
- Use technical terminology

### The Test:
**"Would a business analyst care about this event?"**
- Yes → Domain event
- No → Infrastructure event

---

## 10. Conclusion

This regression represents a common architectural mistake: mixing business and technical concerns. The fix is straightforward but requires careful execution:

1. Move 11 infrastructure events to `infrastructure/events/`
2. Update imports in repository implementations
3. Clean up domain events module
4. Document the distinction clearly

**Estimated Effort**: 2-3 hours
**Risk Level**: Low-Medium
**Business Impact**: None (internal refactoring)
**Technical Debt Reduction**: High
