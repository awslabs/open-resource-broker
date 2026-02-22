# ADR 003: Pydantic in Domain Layer

## Status
Accepted

## Date
2026-02-22

## Context

The domain layer currently uses Pydantic for validation and serialization in 15 files:
- Base classes (Entity, ValueObject, DomainEvent)
- Aggregates (Template, Request, Machine)
- Value objects and metadata classes
- Domain events

This creates a dependency on an external framework, which raises the question: **Is Pydantic an infrastructure dependency that violates clean architecture?**

### Clean Architecture Perspective

**Pure DDD argues:**
- Domain should have zero external dependencies
- Domain objects should be pure Python
- Validation should use domain-specific logic
- Serialization is an infrastructure concern

**Pragmatic perspective argues:**
- Pydantic is a validation library, not infrastructure
- Similar to using stdlib dataclasses
- Provides runtime type checking and validation
- Widely accepted in Python domain modeling
- Reduces boilerplate significantly

### Current State Analysis

**Infrastructure Import Audit:**
- ✅ Zero runtime infrastructure imports in domain layer
- ✅ Ports properly defined for external dependencies
- ✅ Domain services use abstractions
- ⚠️ 15 files depend on Pydantic

**Risk Assessment:**
- Removing Pydantic: HIGH risk, 20+ hours effort, breaks all tests
- Keeping Pydantic: LOW risk, enables focus on real violations
- Hybrid approach: MEDIUM risk, requires ongoing migration work

## Decision

**We accept Pydantic in the domain layer as a validation framework, not as infrastructure.**

### Rationale

1. **Pragmatic Trade-off**: Focus on actual architecture violations (infrastructure imports, tight coupling) rather than framework dependencies

2. **Low Risk**: Keeping Pydantic allows incremental improvements without breaking changes

3. **High Value**: Pydantic provides runtime validation that catches domain rule violations

4. **Industry Practice**: Widely accepted in Python DDD implementations

5. **Reversible**: Can migrate away from Pydantic in future if needed

### Constraints

To ensure Pydantic remains a validation tool and doesn't become infrastructure coupling:

1. **Use for validation only** - No Pydantic-specific infrastructure features
2. **No serialization logic in domain** - Keep serialization in infrastructure layer
3. **Domain-first validation** - Business rules expressed in domain terms
4. **Avoid tight coupling** - Don't use advanced Pydantic features that lock us in
5. **Test without Pydantic** - Domain logic testable independently

### What We Will NOT Do

- ❌ Use Pydantic for database serialization in domain
- ❌ Use Pydantic for API serialization in domain
- ❌ Use Pydantic validators for infrastructure concerns
- ❌ Expose Pydantic types in domain interfaces
- ❌ Use Pydantic-specific features (computed fields, etc.) in domain

### What We WILL Do

- ✅ Use Pydantic for domain validation (business rules)
- ✅ Use Pydantic for immutability (frozen=True for value objects)
- ✅ Use Pydantic for type safety (runtime type checking)
- ✅ Keep serialization adapters in infrastructure layer
- ✅ Document domain rules in validation logic

## Consequences

### Positive

- **Fast delivery**: Focus on real violations, not framework removal
- **Low risk**: No breaking changes, tests continue to work
- **Better validation**: Runtime type checking catches errors early
- **Less boilerplate**: Pydantic reduces code compared to pure Python
- **Team velocity**: Developers familiar with Pydantic

### Negative

- **Framework dependency**: Domain depends on external library
- **Migration cost**: If we change decision, migration will be expensive
- **Testing complexity**: Need to mock Pydantic in some tests
- **Philosophical impurity**: Not "pure" DDD

### Neutral

- **Reversible decision**: Can migrate to pure Python in future sprint
- **Industry standard**: Many Python DDD projects use Pydantic
- **Documentation needed**: Must clearly document constraints

## Alternatives Considered

### Alternative 1: Remove Pydantic (Pure DDD)
**Approach**: Replace all Pydantic with pure Python classes

**Pros**:
- Pure DDD compliance
- No external dependencies
- Full control over validation

**Cons**:
- 20+ hours effort
- High risk of breaking changes
- Significant boilerplate code
- Tests will break during migration
- Low immediate value

**Decision**: Rejected - too high risk for current sprint

### Alternative 2: Adapter Pattern
**Approach**: Keep Pydantic, add pure domain interfaces on top

**Pros**:
- Incremental migration path
- No breaking changes
- Can migrate gradually

**Cons**:
- Adds complexity
- Duplicate code (adapters + Pydantic)
- Ongoing maintenance burden
- Unclear value proposition

**Decision**: Rejected - adds complexity without clear benefit

### Alternative 3: Hybrid (Accepted)
**Approach**: Accept Pydantic with constraints, focus on real violations

**Pros**:
- Fast delivery
- Low risk
- Focus on high-value fixes
- Reversible decision

**Cons**:
- Not pure DDD
- Framework dependency

**Decision**: Accepted - best balance of risk, effort, and value

## Implementation Plan

### Immediate Actions (This Sprint)

1. ✅ Document this ADR
2. ✅ Create domain exception hierarchy
3. ✅ Purify domain events (remove infrastructure details)
4. ✅ Validate domain services use only ports
5. ✅ Update sprint tasks to reflect new scope

### Future Considerations (If Needed)

If we decide to remove Pydantic in the future:

1. **Phase 1**: Create pure domain base classes (Entity, ValueObject, Event)
2. **Phase 2**: Implement adapter pattern for backward compatibility
3. **Phase 3**: Migrate aggregates one at a time
4. **Phase 4**: Migrate value objects and events
5. **Phase 5**: Remove Pydantic dependency

**Estimated Effort**: 3-4 sprints (60-80 hours)

## Review Date

**Next Review**: 2026-06-01 (4 months)

**Review Criteria**:
- Has Pydantic caused any architecture issues?
- Have we needed features Pydantic doesn't provide?
- Has the team expressed concerns about Pydantic?
- Are there new alternatives worth considering?

## References

- Clean Architecture by Robert Martin
- Domain-Driven Design by Eric Evans
- Pydantic Documentation
- Python DDD with Pydantic (Cosmic Python)

## Notes

This decision prioritizes **pragmatism over purity**. We acknowledge that pure DDD would avoid framework dependencies, but we accept this trade-off to:

1. Deliver value faster
2. Reduce risk
3. Focus on actual architecture violations
4. Maintain team velocity

This is a **reversible decision** - we can migrate away from Pydantic in a future sprint if the costs outweigh the benefits.
