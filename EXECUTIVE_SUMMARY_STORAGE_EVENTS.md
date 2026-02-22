# Executive Summary: Storage Events Architecture Regression

**Date**: 2026-02-22
**Severity**: Medium-High
**Effort**: 2-3 hours
**Risk**: Low-Medium

---

## The Problem

The domain layer contains 13 event classes in `src/domain/base/events/storage_events.py` that violate Domain-Driven Design principles by mixing business logic with infrastructure concerns.

### What's Wrong

```
domain/base/events/storage_events.py contains:
├── RepositoryOperationStartedEvent      ❌ Infrastructure
├── RepositoryOperationCompletedEvent    ❌ Infrastructure  
├── RepositoryOperationFailedEvent       ❌ Infrastructure
├── SlowQueryDetectedEvent               ❌ Infrastructure
├── TransactionStartedEvent              ❌ Infrastructure
├── TransactionCommittedEvent            ❌ Infrastructure
├── StorageStrategySelectedEvent         ❌ Infrastructure
├── StorageStrategyFailoverEvent         ❌ Infrastructure
├── ConnectionPoolEvent                  ❌ Infrastructure
├── StoragePerformanceEvent              ❌ Infrastructure
├── StorageHealthCheckEvent              ❌ Infrastructure
├── StorageEvent (base class)            ❌ Infrastructure
└── StorageStrategyEvent (base class)    ❌ Infrastructure
```

**None of these are domain business events.**

---

## The Test: Would a Business Analyst Care?

### Infrastructure Events (Technical Telemetry)
- "The database query took 500ms" → NO
- "Connection pool exhausted" → NO
- "Failover from SQL to DynamoDB" → NO
- "Transaction committed" → NO

### Domain Events (Business State Changes)
- "Request was submitted" → YES
- "Machine was provisioned" → YES
- "Template validation failed" → YES
- "Request timed out" → YES

**Rule**: If a business analyst doesn't care, it's not a domain event.

---

## The Solution

### Move Infrastructure Events to Infrastructure Layer

```
BEFORE (Wrong):
domain/base/events/
├── storage_events.py  ← Contains infrastructure monitoring
└── domain_events.py   ← Contains business events

AFTER (Correct):
domain/base/events/
└── domain_events.py   ← Only business events

infrastructure/events/
└── storage_events.py  ← Infrastructure monitoring events
```

### Impact Analysis

**Files Affected**: 
- Create: `src/infrastructure/events/storage_events.py`
- Update: `src/infrastructure/storage/repositories/request_repository.py`
- Update: `src/domain/base/events/__init__.py`
- Delete: `src/domain/base/events/storage_events.py`

**Import Changes**:
```python
# OLD
from domain.base.events import RepositoryOperationStartedEvent

# NEW  
from infrastructure.events.storage_events import RepositoryOperationStartedEvent
```

**Runtime Impact**: None (internal refactoring only)

---

## Why This Matters

### Current Problems

1. **Domain Pollution**: Domain layer contains technical infrastructure details
2. **Confusion**: Developers can't distinguish business from technical events
3. **Maintenance**: Domain becomes harder to understand and evolve
4. **DDD Violation**: Breaks fundamental separation of concerns

### After Fix

1. **Clear Boundaries**: Domain contains only business logic
2. **Better Understanding**: New developers immediately see the distinction
3. **Easier Evolution**: Infrastructure can change without affecting domain
4. **DDD Compliance**: Proper layered architecture

---

## Classification Summary

### 11 Infrastructure Events → Move to `infrastructure/events/`

**Repository Operations** (4 events):
- Track database operation lifecycle and performance
- Used for monitoring, debugging, optimization
- Business doesn't care about "slow queries"

**Transactions** (2 events):
- Track database transaction lifecycle
- Technical implementation detail
- Business thinks in terms of "request completed", not "transaction committed"

**Storage Strategy** (3 events):
- Track which storage backend is used (JSON/SQL/DynamoDB)
- Track failover between backends
- Business doesn't care about storage implementation

**Monitoring** (2 events):
- Connection pool health
- Storage health checks
- Pure operational telemetry

### 0 Domain Events → Nothing stays in domain

The current file contains NO domain business events. All 13 events are infrastructure concerns.

---

## Implementation Approach

### Phase 1: Create Infrastructure Module (30 min)
1. Create `src/infrastructure/events/storage_events.py`
2. Copy all 13 events with proper documentation
3. Add clear comments explaining they're infrastructure events

### Phase 2: Update Imports (30 min)
1. Update `src/infrastructure/storage/repositories/request_repository.py`
2. Update any other repository implementations
3. Update test files

### Phase 3: Clean Domain Layer (15 min)
1. Remove storage events from `src/domain/base/events/__init__.py`
2. Delete `src/domain/base/events/storage_events.py`
3. Verify no broken imports

### Phase 4: Verify (15 min)
1. Run full test suite
2. Check for import errors
3. Verify event publishing still works

### Phase 5: Document (30 min)
1. Update `src/domain/README.md`
2. Update `src/infrastructure/README.md`
3. Create ADR documenting the decision

**Total Time**: ~2 hours

---

## Risk Assessment

### Low Risk ✅
- Events only used for logging/monitoring
- No business logic depends on these events
- Event publisher handles all types uniformly
- Easy to rollback if needed

### Medium Risk ⚠️
- Import changes across multiple files
- Need to find all usages
- Potential for missed imports

### Mitigation Strategy
1. Use grep to find ALL usages before starting
2. Make changes in single atomic commit
3. Run full test suite before committing
4. Have rollback plan ready

---

## Success Criteria

### Technical
- [ ] All tests pass
- [ ] No import errors
- [ ] Event publishing works correctly
- [ ] Repository operations emit events

### Architectural
- [ ] Domain layer contains only business events
- [ ] Infrastructure events in infrastructure layer
- [ ] Clear documentation of distinction
- [ ] ADR created

### Quality
- [ ] Code review approved
- [ ] Documentation updated
- [ ] Examples provided
- [ ] Future guidance clear

---

## Key Decisions

### Decision 1: Keep InfrastructureEvent Inheritance
**Rationale**: Event publisher needs common interface. Infrastructure events are still "events", just not business events. The inheritance is correct; the file location was wrong.

### Decision 2: Move ALL Storage Events
**Rationale**: None of the 13 events represent business state changes. All are technical monitoring. No exceptions.

### Decision 3: Don't Create Domain Persistence Events (Yet)
**Rationale**: Domain should be persistence-ignorant. Only add domain persistence events if business logic needs to react to persistence failures.

### Decision 4: Single Atomic Migration
**Rationale**: Partial migration creates confusion. Do it all at once in one commit.

---

## Long-term Guidance

### For Future Developers

**When creating a new event, ask:**

1. **Would a business analyst care about this?**
   - Yes → Domain event (`domain/base/events/`)
   - No → Infrastructure event (`infrastructure/events/`)

2. **Does it describe business state change or technical operation?**
   - Business state → Domain event
   - Technical operation → Infrastructure event

3. **Does it use business or technical terminology?**
   - Business terms (request, machine, template) → Domain event
   - Technical terms (query, transaction, connection) → Infrastructure event

4. **Would business logic react to this event?**
   - Yes → Domain event
   - No → Infrastructure event

### Examples

**Domain Events** ✅
```python
class RequestSubmittedEvent(DomainEvent):
    """A user submitted a new request."""
    request_id: str
    user_id: str
    
class MachineProvisioningFailedEvent(DomainEvent):
    """Machine could not be provisioned."""
    machine_id: str
    reason: str  # Business reason
```

**Infrastructure Events** ✅
```python
class RepositoryOperationFailedEvent(InfrastructureEvent):
    """Database operation failed."""
    operation_id: str
    error_details: dict
    
class SlowQueryDetectedEvent(InfrastructureEvent):
    """Query exceeded performance threshold."""
    query_time_ms: float
    threshold_ms: float
```

---

## Recommendation

**Proceed with migration immediately.**

This is a straightforward refactoring with:
- Clear benefits (architectural clarity)
- Low risk (no runtime changes)
- Reasonable effort (2-3 hours)
- High value (technical debt reduction)

The longer we wait, the more code will depend on the wrong structure.

---

## Next Steps

1. Review this analysis with team
2. Get approval to proceed
3. Schedule 3-hour block for migration
4. Execute implementation plan
5. Create PR with changes
6. Update team documentation

---

## Questions?

**Q: Can we do this incrementally?**
A: Not recommended. Partial migration creates confusion. Do it all at once.

**Q: Will this break anything?**
A: No runtime changes. Only import paths change. Tests will catch any issues.

**Q: What if we find more infrastructure events in domain?**
A: Apply the same test: "Would a business analyst care?" If no, move to infrastructure.

**Q: How do we prevent this in the future?**
A: Clear documentation, code review guidelines, and the "business analyst test".

---

**Prepared by**: Principal Engineer (Architecture Review)
**Date**: 2026-02-22
**Status**: Ready for Implementation
