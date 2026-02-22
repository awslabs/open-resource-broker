# Quick Reference: Domain vs Infrastructure Events

## The Golden Rule

**"Would a business analyst care about this event?"**
- YES → Domain Event (`domain/base/events/`)
- NO → Infrastructure Event (`infrastructure/events/`)

---

## Domain Events (Business Logic)

### Characteristics
- Represent business-significant state changes
- Use business terminology
- Trigger business workflows
- Understandable by non-technical stakeholders
- Describe WHAT happened to business entities

### Location
`src/domain/base/events/domain_events.py`

### Examples
```python
✅ RequestCreatedEvent          # Business: new request submitted
✅ MachineProvisionedEvent      # Business: machine became available
✅ TemplateValidatedEvent       # Business: template passed validation
✅ RequestCompletedEvent        # Business: request finished successfully
✅ MachineTerminatedEvent       # Business: machine was shut down
✅ RequestTimeoutEvent          # Business: request exceeded time limit
```

### When to Create
- User performs an action
- Business rule is enforced
- Business state changes
- Business workflow needs to react
- Audit trail for business operations

---

## Infrastructure Events (Technical Monitoring)

### Characteristics
- Track technical operations and performance
- Use technical terminology
- Support monitoring and debugging
- Only relevant to technical staff
- Describe HOW the system performed

### Location
`src/infrastructure/events/storage_events.py`

### Examples
```python
✅ RepositoryOperationStartedEvent    # Tech: DB operation began
✅ RepositoryOperationCompletedEvent  # Tech: DB operation finished
✅ SlowQueryDetectedEvent             # Tech: query exceeded threshold
✅ TransactionCommittedEvent          # Tech: DB transaction committed
✅ StorageStrategySelectedEvent       # Tech: chose JSON vs SQL vs DynamoDB
✅ StorageStrategyFailoverEvent       # Tech: failed over to backup storage
✅ ConnectionPoolEvent                # Tech: connection pool status
✅ StorageHealthCheckEvent            # Tech: storage backend health
```

### When to Create
- Performance monitoring needed
- Debugging information required
- Health checks and alerts
- Resource utilization tracking
- Technical operations logging

---

## Decision Tree

```
New Event Needed?
│
├─ Does it describe a business state change?
│  ├─ YES → Domain Event
│  └─ NO → Continue...
│
├─ Would business logic react to it?
│  ├─ YES → Domain Event
│  └─ NO → Continue...
│
├─ Would a business analyst understand it?
│  ├─ YES → Domain Event
│  └─ NO → Continue...
│
├─ Does it use business terminology?
│  ├─ YES → Domain Event
│  └─ NO → Infrastructure Event
│
└─ Is it for monitoring/debugging?
   ├─ YES → Infrastructure Event
   └─ NO → Re-evaluate (might not need event)
```

---

## Common Mistakes

### ❌ Wrong: Infrastructure Event in Domain
```python
# In domain/base/events/domain_events.py
class SlowQueryDetectedEvent(DomainEvent):  # WRONG!
    query_time_ms: float
    threshold_ms: float
```
**Why Wrong**: Business doesn't care about query performance. This is technical monitoring.

### ✅ Right: Infrastructure Event in Infrastructure
```python
# In infrastructure/events/storage_events.py
class SlowQueryDetectedEvent(InfrastructureEvent):  # CORRECT!
    query_time_ms: float
    threshold_ms: float
```

### ❌ Wrong: Domain Event in Infrastructure
```python
# In infrastructure/events/storage_events.py
class RequestSubmittedEvent(InfrastructureEvent):  # WRONG!
    request_id: str
    user_id: str
```
**Why Wrong**: Request submission is a business event. Business logic needs to react to it.

### ✅ Right: Domain Event in Domain
```python
# In domain/base/events/domain_events.py
class RequestCreatedEvent(DomainEvent):  # CORRECT!
    request_id: str
    user_id: str
```

---

## Terminology Guide

### Business Terms → Domain Events
- Request, Machine, Template
- Created, Submitted, Provisioned, Validated
- Completed, Failed, Timeout
- User, Customer, Resource
- Status, State, Configuration

### Technical Terms → Infrastructure Events
- Repository, Transaction, Query
- Connection, Pool, Strategy
- Performance, Throughput, Latency
- Health Check, Failover, Monitoring
- Database, Storage, Backend

---

## Real-World Scenarios

### Scenario 1: Request Fails to Save
**Question**: What events should fire?

**Domain Event** ✅
```python
RequestPersistenceFailedEvent(
    request_id="req-123",
    reason="storage_unavailable"  # Business-level reason
)
```
**Why**: Business needs to know the request couldn't be saved. May need to notify user or retry.

**Infrastructure Event** ✅
```python
RepositoryOperationFailedEvent(
    operation_id="op-456",
    entity_type="Request",
    entity_id="req-123",
    error_message="Connection timeout",  # Technical details
    storage_strategy="SQL"
)
```
**Why**: Operations team needs technical details for debugging.

**Both events fire** - they serve different purposes.

### Scenario 2: Query Takes 5 Seconds
**Question**: What event should fire?

**Infrastructure Event Only** ✅
```python
SlowQueryDetectedEvent(
    operation_id="op-789",
    query_time_ms=5000,
    threshold_ms=1000,
    query_details={"table": "requests", "operation": "find"}
)
```
**Why**: This is pure performance monitoring. Business doesn't care about query speed.

**No Domain Event** - unless the slowness causes a business impact (like timeout).

### Scenario 3: Machine Provisioning Completes
**Question**: What events should fire?

**Domain Event** ✅
```python
MachineProvisionedEvent(
    machine_id="m-123",
    private_ip="10.0.1.5",
    provisioning_time=datetime.now()
)
```
**Why**: Business cares that the machine is ready. This may trigger workflows.

**Infrastructure Event** ✅
```python
RepositoryOperationCompletedEvent(
    operation_id="op-999",
    entity_type="Machine",
    entity_id="m-123",
    storage_strategy="DynamoDB",
    duration_ms=150
)
```
**Why**: Operations team tracks that the save operation succeeded.

**Both events fire** - different audiences, different purposes.

---

## Import Patterns

### Domain Events
```python
# Correct
from domain.base.events import (
    RequestCreatedEvent,
    MachineProvisionedEvent,
    TemplateValidatedEvent,
)

# Used in: Application services, domain services, aggregates
```

### Infrastructure Events
```python
# Correct
from infrastructure.events.storage_events import (
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
    StorageStrategyFailoverEvent,
)

# Used in: Repositories, storage adapters, infrastructure services
```

---

## Code Review Checklist

When reviewing event-related code:

- [ ] Event is in correct layer (domain vs infrastructure)
- [ ] Event name uses appropriate terminology
- [ ] Event documentation explains business vs technical purpose
- [ ] Event is imported from correct module
- [ ] Event is published by appropriate layer
- [ ] Event handlers are in appropriate layer

---

## Migration Checklist

When moving events between layers:

- [ ] Identify all usages with grep
- [ ] Update event file location
- [ ] Update all import statements
- [ ] Update event module __init__.py
- [ ] Update documentation
- [ ] Run tests
- [ ] Update examples
- [ ] Create ADR if significant

---

## FAQ

**Q: Can infrastructure events inherit from DomainEvent?**
A: Yes. `InfrastructureEvent` inherits from `DomainEvent` for the event publisher to work. The inheritance is correct; the file location matters.

**Q: Should every repository operation emit events?**
A: Infrastructure events: Yes (for monitoring). Domain events: Only if business logic needs to react.

**Q: Can domain code import infrastructure events?**
A: No. Domain should never depend on infrastructure. Only infrastructure can import infrastructure events.

**Q: Can infrastructure code import domain events?**
A: Yes. Infrastructure implements domain ports and can publish domain events.

**Q: What if an event seems like both?**
A: Create two events - one domain, one infrastructure. They serve different purposes.

**Q: How do I prevent mixing them again?**
A: Use this guide, code reviews, and the "business analyst test".

---

## Summary

| Aspect | Domain Events | Infrastructure Events |
|--------|---------------|----------------------|
| **Location** | `domain/base/events/` | `infrastructure/events/` |
| **Purpose** | Business state changes | Technical monitoring |
| **Audience** | Business + Developers | Developers + Ops |
| **Terminology** | Business terms | Technical terms |
| **Triggers** | Business workflows | Monitoring/alerting |
| **Examples** | Request created, Machine provisioned | Query slow, Connection failed |
| **Test** | Business analyst cares | Only tech team cares |

---

**Remember**: When in doubt, ask "Would a business analyst care?" If no, it's infrastructure.

---

**Last Updated**: 2026-02-22
**Version**: 1.0
**Status**: Active Reference
