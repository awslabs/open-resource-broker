# QA Test Report: Request and Machine Operations

**Date:** 2026-02-18  
**Scope:** All `orb requests` and `orb machines` commands and subcommands  
**Test Environment:** Open Resource Broker CLI  

## Executive Summary

Comprehensive testing of request and machine operations reveals **7 critical issues** requiring immediate attention, along with several minor inconsistencies. The core functionality works correctly, but there are significant usability and consistency problems.

## Test Coverage

### Commands Tested
- **Requests:** `list`, `show`, `status`, `cancel`
- **Machines:** `list`, `show`, `status`, `request`, `return`

### Test Scenarios
- Basic functionality
- Pagination (`--limit`, `--offset`)
- Filtering (`--status`, `--template-id`, `--filter`)
- Multiple ID patterns (space-separated, flag-based, mixed)
- Output formats (`json`, `yaml`, `table`, `list`)
- Edge cases and error conditions
- Help text quality
- Argument parsing validation

## Critical Issues Found

### 1. **CRITICAL: Inconsistent Behavior Between `requests status` and `machines status`**

**Issue:** Commands behave completely differently when no IDs provided:
- `orb requests status` → **ERROR:** "request_id is required"
- `orb machines status` → **SUCCESS:** Returns all machines (same as `machines list`)

**Impact:** Breaks user expectations and CLI consistency
**Severity:** HIGH - Confusing UX, inconsistent behavior

### 2. **CRITICAL: `requests show` Command Broken**

**Issue:** `orb requests show <request-id>` returns generic error instead of request details:
```json
{"message": "Request failed: Unknown error"}
```

**Expected:** Detailed request information like `requests status` provides
**Impact:** Core functionality broken
**Severity:** HIGH - Command completely non-functional

### 3. **CRITICAL: `machines show` Returns Wrong Response Format**

**Issue:** `orb machines show <machine-id>` returns request-style response:
```json
{
  "requestId": "req-586271a5-f198-4361-be48-18a0daf9392e",
  "message": "Request submitted for processing"
}
```

**Expected:** Machine details like `machines status` provides
**Impact:** Command returns wrong data type
**Severity:** HIGH - Misleading response format

### 4. **CRITICAL: Help Text Inconsistency - FLAG_REQUEST_IDS**

**Issue:** Help text shows internal variable name instead of user-friendly description:
```
--request-id FLAG_REQUEST_IDS, -r FLAG_REQUEST_IDS
                        Request ID to check
```

**Expected:** `--request-id REQUEST_ID, -r REQUEST_ID`
**Impact:** Confusing help text, looks like a bug
**Severity:** MEDIUM - Poor UX, unprofessional appearance

### 5. **CRITICAL: Help Text Inconsistency - FLAG_MACHINE_IDS**

**Issue:** Same issue in machines commands:
```
--machine-id FLAG_MACHINE_IDS, -m FLAG_MACHINE_IDS
                        Machine ID to check
```

**Expected:** `--machine-id MACHINE_ID, -m MACHINE_ID`
**Impact:** Confusing help text, looks like a bug
**Severity:** MEDIUM - Poor UX, unprofessional appearance

### 6. **CRITICAL: Output Format Inconsistency**

**Issue:** `--format table` and `--format yaml` work, but output is still JSON for some commands
**Test Results:**
- `orb requests list --format table` → Still outputs JSON
- `orb machines list --format yaml` → Correctly outputs YAML

**Impact:** Inconsistent format handling across commands
**Severity:** MEDIUM - Feature partially broken

### 7. **CRITICAL: Validation Inconsistency Between Commands**

**Issue:** Different validation behavior for invalid IDs:
- `orb requests status invalid-id` → **Pydantic validation error** (detailed)
- `orb machines status invalid-id` → **Empty result** (silent failure)

**Impact:** Inconsistent error handling, silent failures
**Severity:** MEDIUM - Poor error UX, debugging difficulty

## Working Features ✅

### Multiple ID Support Patterns
All documented patterns work correctly:

**✅ Space-Separated IDs:**
```bash
orb requests status req-1 req-2 req-3
orb machines status i-1 i-2 i-3
```

**✅ Flag-Based Multiple IDs:**
```bash
orb requests status -r req-1 -r req-2 -r req-3
orb machines status -m i-1 -m i-2 -m i-3
```

**✅ Mixed Patterns:**
```bash
orb requests status req-1 -r req-2 --request-id req-3
orb machines status i-1 -m i-2 --machine-id i-3
```

**❌ Comma-Separated (Correctly Rejected):**
```bash
orb requests status req-1,req-2,req-3  # Validation error (expected)
```

### Pagination
**✅ Working correctly:**
```bash
orb requests list --limit 5
orb requests list --limit 3 --offset 5
orb machines list --limit 3
```

### Filtering
**✅ Status filtering:**
```bash
orb requests list --status failed --limit 2
orb machines list --status running --limit 2
```

**✅ Generic filtering:**
```bash
orb requests list --filter "template_id~EC2Fleet" --limit 2
```

### Output Formats
**✅ YAML format works:**
```bash
orb machines list --limit 2 --format yaml
```

**❌ Table format broken** (outputs JSON instead)

### Error Handling
**✅ Proper validation for request IDs:**
- Invalid format rejected with clear Pydantic error
- Detailed error messages with validation rules

**❌ Silent failure for machine IDs:**
- Invalid machine IDs return empty results instead of errors

## Minor Issues

### 1. **Help Text Quality**
- Most help text is clear and comprehensive
- Good coverage of global arguments
- Examples provided for filter syntax
- **Issue:** Internal variable names leak through in some places

### 2. **Argument Conflicts**
- No conflicts found between global and command-specific arguments
- All argument combinations work as expected

### 3. **Edge Cases**
- Empty result sets handled gracefully
- Large result sets work with pagination
- **Issue:** Inconsistent behavior when no arguments provided

## Data Quality Observations

### Request Data
- 196 requests in database, all with `status: "failed"`
- Two types of failures:
  1. "Unable to locate credentials" (older requests)
  2. "argument of type 'method' is not iterable" (newer requests)
- All requests have `providerApi: null` (potential data issue)

### Machine Data
- 37+ machines in database with mixed statuses
- Status distribution: `pending`, `running`, `shutting-down`
- Good variety of provider APIs: `RunInstances`, `EC2Fleet`
- Rich metadata: IPs, DNS names, launch times, etc.

## Recommendations

### Immediate Fixes (P0 - Critical)
1. **Fix `requests show` command** - Should return detailed request info
2. **Fix `machines show` command** - Should return machine details, not request info
3. **Standardize no-args behavior** - Both status commands should behave consistently
4. **Fix help text variable names** - Remove FLAG_* internal names

### High Priority (P1)
5. **Fix output format handling** - Table format should actually output tables
6. **Standardize validation** - Machine commands should validate IDs like request commands
7. **Improve error messages** - Consistent error handling across all commands

### Medium Priority (P2)
8. **Add table format implementation** - Currently outputs JSON despite `--format table`
9. **Improve silent failure handling** - Invalid machine IDs should return errors
10. **Add more comprehensive validation** - Validate template IDs, machine counts, etc.

## Test Data Summary

### Requests
- **Total:** 196 requests
- **Status:** 100% failed
- **Date Range:** 2026-01-28 to 2026-02-02
- **Templates:** EC2Fleet-Instant-OnDemand, RunInstances-OnDemand
- **Providers:** aws_default_us-east-1, null

### Machines
- **Total:** 37+ machines
- **Status Distribution:** 
  - `running`: ~15 machines
  - `pending`: ~20 machines  
  - `shutting-down`: ~2 machines
- **Provider APIs:** RunInstances, EC2Fleet
- **Provider:** aws_flamurg-testing-Admin_eu-west-2

## Conclusion

The Open Resource Broker request and machine operations have solid core functionality with good support for multiple ID patterns, pagination, and filtering. However, **7 critical issues** significantly impact usability and consistency. The most severe problems are broken `show` commands and inconsistent behavior patterns that will confuse users.

**Priority:** Address the 4 critical functional issues first (broken commands, inconsistent behavior), then tackle the 3 UX issues (help text, validation, formatting).

**Overall Assessment:** Core functionality works, but critical UX and consistency issues prevent production readiness.