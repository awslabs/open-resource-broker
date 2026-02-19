# --all Flag Audit Report

**Date**: 2026-02-19  
**Analyst**: orb-architect  
**Status**: ANALYSIS COMPLETE (CORRECTED)

## Executive Summary

- **Working**: 3/3 implemented --all flags work correctly
- **Missing**: 1 high-priority --all implementation needed
- **Broken**: 0 broken implementations found
- **Clarifications**: Stop/start commands don't exist, validate needs enhancement

---

## Currently Working

### 1. requests status --all ✅
- **Command**: `orb requests status --all`
- **Behavior**: Shows all requests with provider sync
- **Validation**: Prevents --all with specific IDs
- **Status**: WORKING (recently fixed)

### 2. machines status --all ✅
- **Command**: `orb machines status --all`
- **Behavior**: Shows all machines with status sync
- **Validation**: Prevents --all with specific IDs
- **Status**: WORKING

### 3. machines return --all ✅
- **Command**: `orb machines return --all --force`
- **Behavior**: Returns (terminates) all active machines
- **Validation**: Requires --force flag for safety
- **Status**: WORKING
- **Note**: "Return" is HostFactory terminology for terminate

---

## Missing Implementations

### P1: High Priority

#### Templates Validate Loaded Templates
**Missing**: `orb templates validate --all` and `orb templates validate template-id`

**Why Needed**:
- Validate templates already loaded in system
- Catch configuration errors in existing templates
- Quality assurance for deployed templates

**Current State**: 
- Only validates external files: `orb templates validate --file template.json`
- This is for pre-import validation

**Enhancement Needed**:
- Keep existing --file functionality (pre-import validation)
- Add support for validating loaded templates (post-import validation)
- `orb templates validate template-id` - validate specific loaded template
- `orb templates validate --all` - validate all loaded templates

**Implementation**:
- Modify validate handler to support both modes
- Without --file: validate loaded templates
- With --file: validate external file (current behavior)

---

### P2: Medium Priority

#### Standardize Safety Patterns
**Issue**: Inconsistent --force requirements

**Current**:
- `machines return --all` requires --force ✅
- Other destructive operations may not

**Recommendation**:
- Require --force for all destructive --all operations
- Document safety requirements clearly
- Consistent user experience

---

### P3: Low Priority

#### Machine Terminate Alias
**Issue**: No explicit terminate command (only "return")

**Current**: `machines return` handles termination

**Clarification**:
- "Return" is HostFactory standard terminology
- Means "return machines to provider" = terminate/destroy
- Not ORB-specific, this is how HostFactory works

**Recommendation**:
- Keep `machines return` as primary (HostFactory standard)
- Could add `machines terminate` as alias for clarity
- Both would do same thing
- Priority: P3 (nice-to-have)

---

## Clarifications

### 1. Stop/Start Commands
**CORRECTION**: We do NOT have stop/start commands.
- Architect was incorrect in original report
- Not relevant to --all flag audit
- Separate decision if we want to add them in future

### 2. Templates Validate Purpose
**Current**: Validates external template files before import
**Enhancement**: Should also validate loaded templates in system
**User's Point**: Valid - validate should work on loaded templates too

### 3. Return vs Terminate
**Clarification**: "Return" is HostFactory terminology
- Return = terminate/destroy machines
- Standard HostFactory vocabulary
- Not confusing to HostFactory users
- Could add terminate alias for non-HostFactory users

---

## Implementation Priority

### Immediate (P1)

1. **Add templates validate for loaded templates**
   - `orb templates validate template-id` - validate specific template
   - `orb templates validate --all` - validate all templates
   - Keep existing --file functionality
   - Report validation results

### Future (P2-P3)

2. **Standardize safety patterns** (P2)
   - Audit all destructive operations
   - Add --force requirements consistently
   - Update documentation

3. **Consider terminate alias** (P3)
   - Add `machines terminate` as alias to `machines return`
   - Improve clarity for non-HostFactory users

---

## Commands That Don't Need --all

### List Commands
These already show all by default:
- `orb requests list`
- `orb machines list`
- `orb templates list`
- `orb providers list`

### Single-Target Commands
These operate on single resources:
- `orb templates create`
- `orb templates update`
- `orb templates delete`
- `orb machines request`

### Global Commands
These are already global:
- `orb templates refresh` (refreshes all)
- `orb templates generate` (generates all)
- `orb system health`

---

## Next Steps

1. Create task for templates validate enhancement (P1)
2. Review safety patterns (P2)
3. Update documentation
4. Consider P3 enhancements

---

**Document Version**: 1.1 (Corrected)  
**Last Updated**: 2026-02-19  
**Status**: READY FOR TASK CREATION
