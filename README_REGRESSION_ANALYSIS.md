# Regression 1 Analysis: Storage Events Infrastructure Leak

## Quick Start

This directory contains a complete architectural analysis of the storage events regression found in the domain layer.

### Problem
13 infrastructure monitoring events are incorrectly placed in `src/domain/base/events/storage_events.py`, violating Domain-Driven Design principles.

### Solution
Move all 13 events to `src/infrastructure/events/storage_events.py` where they belong.

### Documents

Read these in order based on your role:

#### For Decision Makers (5 min read)
**EXECUTIVE_SUMMARY_STORAGE_EVENTS.md**
- What's wrong and why it matters
- Solution overview and timeline
- Risk assessment and recommendation

#### For Architects & Senior Engineers (15 min read)
**ANALYSIS_STORAGE_EVENTS_REGRESSION.md**
- Detailed event classification
- Architecture decisions and rationale
- Alternative approaches considered
- Long-term guidance

#### For Implementation Engineers (20 min read)
**IMPLEMENTATION_GUIDE_STORAGE_EVENTS.md**
- Step-by-step migration instructions
- Code examples and import patterns
- Verification procedures
- Rollback plan

#### For All Developers (10 min read, keep handy)
**QUICK_REFERENCE_DOMAIN_VS_INFRASTRUCTURE_EVENTS.md**
- Decision tree for event classification
- Common mistakes and corrections
- Real-world scenarios and FAQ
- Code review checklist

#### Master Summary (10 min read)
**REGRESSION_1_COMPLETE_ANALYSIS.md**
- Complete overview of all analysis
- Implementation roadmap
- Success metrics and next actions

---

## The Golden Rule

**"Would a business analyst care about this event?"**
- YES → Domain Event (`domain/base/events/`)
- NO → Infrastructure Event (`infrastructure/events/`)

---

## Key Findings

### All 13 Events Are Infrastructure

| Category | Events | Why Infrastructure |
|----------|--------|-------------------|
| Repository Operations | 4 | Database performance monitoring |
| Transactions | 2 | Technical implementation detail |
| Storage Strategy | 3 | Backend selection is technical |
| Monitoring | 2 | Operational telemetry |
| Base Classes | 2 | Support infrastructure events |

**Result**: 0 domain events, 13 infrastructure events in wrong location

---

## Impact

- **Severity**: Medium-High (architectural violation)
- **Effort**: 2-3 hours (straightforward refactoring)
- **Risk**: Low-Medium (no runtime changes)
- **Business Impact**: None (internal refactoring)

---

## Recommendation

**Proceed with migration immediately.**

Benefits:
- Clearer architecture
- Better separation of concerns
- Easier for new developers
- Reduced technical debt

The longer we wait, the more code will depend on the incorrect structure.

---

## Implementation Timeline

1. **Preparation** (15 min): Review docs, get approval
2. **Create Infrastructure Module** (30 min): New event files
3. **Update Imports** (30 min): Fix all import statements
4. **Clean Domain Layer** (15 min): Remove from domain
5. **Verification** (15 min): Run tests, verify
6. **Documentation** (30 min): Update READMEs, create ADR
7. **Review & Merge** (30 min): PR and code review

**Total**: ~2.5 hours

---

## Files Affected

- **Create**: `src/infrastructure/events/storage_events.py`
- **Update**: `src/infrastructure/storage/repositories/request_repository.py`
- **Update**: `src/domain/base/events/__init__.py`
- **Delete**: `src/domain/base/events/storage_events.py`
- **Update**: Test files (imports only)

---

## Quick Classification Examples

### Domain Events ✅
```python
RequestCreatedEvent          # Business: user submitted request
MachineProvisionedEvent      # Business: machine became available
TemplateValidatedEvent       # Business: template passed validation
```

### Infrastructure Events ✅
```python
RepositoryOperationStartedEvent    # Tech: DB operation began
SlowQueryDetectedEvent             # Tech: query exceeded threshold
StorageStrategyFailoverEvent       # Tech: failed over to backup
```

---

## Next Steps

1. **Read** the appropriate document for your role
2. **Review** with team and get approval
3. **Schedule** 3-hour implementation block
4. **Execute** following the implementation guide
5. **Verify** all tests pass
6. **Document** in ADR and update team docs

---

## Questions?

- Check the **Quick Reference** for classification questions
- Check the **Implementation Guide** for technical questions
- Check the **FAQ** section in any document
- Consult with architecture team

---

## Document Sizes

- Executive Summary: 9.3 KB (quick read)
- Detailed Analysis: 9.3 KB (comprehensive)
- Implementation Guide: 17 KB (step-by-step)
- Quick Reference: 8.8 KB (ongoing reference)
- Complete Analysis: 13 KB (master summary)

**Total**: ~58 KB of comprehensive analysis

---

**Analysis Date**: 2026-02-22
**Status**: Complete - Ready for Implementation
**Prepared by**: Principal Engineer (Architecture Review)
