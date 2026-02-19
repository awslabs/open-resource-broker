# --all Flag Audit Report

**Date**: 2026-02-19  
**Analyst**: orb-architect  
**Status**: ANALYSIS COMPLETE

## Executive Summary

- **Working**: 3/3 implemented --all flags work correctly
- **Missing**: 2 high-priority --all implementations needed
- **Broken**: 0 broken implementations found
- **Safety**: Good validation patterns, some inconsistency

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
- **Behavior**: Returns all active machines
- **Validation**: Requires --force flag for safety
- **Status**: WORKING

---

## Missing Implementations

### P1: High Priority

#### 1. Machine Stop/Start Commands
**Missing**: `orb machines stop --all` and `orb machines start --all`

**Why Needed**:
- Stop all machines for cost savings
- Start all stopped machines to resume work
- Common operational tasks

**Current State**: Commands don't exist at all

**Implementation Needed**:
- Add CLI parser entries
- Create handlers for stop/start operations
- Support both individual IDs and --all flag
- Add --force requirement for stop --all

---

#### 2. Templates Validate --all
**Missing**: `orb templates validate --all`

**Why Needed**:
- Validate all templates in system
- Catch configuration errors across all templates
- Quality assurance

**Current State**: Only validates single template from file

**Implementation Needed**:
- Modify existing validate handler
- Add --all flag support
- Iterate through all templates
- Report validation results

---

### P2: Medium Priority

#### 3. Standardize Safety Patterns
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

#### 4. Machine Terminate Command
**Issue**: No explicit terminate command

**Current**: `machines return` handles termination

**Recommendation**:
- Add `machines terminate` as alias to `machines return`
- Or document that return=terminate
- Improve clarity for users

---

## Implementation Priority

### Immediate (P1)

1. **Add machine stop command**
   - `orb machines stop [machine-ids...] [--all] [--force]`
   - Stop running machines
   - Requires --force for --all

2. **Add machine start command**
   - `orb machines start [machine-ids...] [--all]`
   - Start stopped machines
   - No --force needed (not destructive)

3. **Add templates validate --all**
   - `orb templates validate --all`
   - Validate all templates
   - Report validation results

### Future (P2-P3)

4. **Standardize safety patterns** (P2)
   - Audit all destructive operations
   - Add --force requirements consistently
   - Update documentation

5. **Consider terminate alias** (P3)
   - Add explicit terminate command
   - Or improve documentation

---

## Safety Patterns

### Current Good Practices

1. **Validation**: Prevents --all with specific IDs
   ```
   Error: Cannot use --all with specific IDs
   ```

2. **Force Flag**: Destructive operations require --force
   ```
   orb machines return --all --force
   ```

3. **Confirmation**: Interactive prompts for destructive actions

### Recommendations

- Apply --force pattern to all destructive --all operations
- Document safety requirements in help text
- Consider dry-run mode for testing

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

1. Create tasks for P1 implementations:
   - machines stop --all
   - machines start --all
   - templates validate --all

2. Review safety patterns (P2)

3. Update documentation

4. Consider P3 enhancements

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-19  
**Status**: READY FOR TASK CREATION
