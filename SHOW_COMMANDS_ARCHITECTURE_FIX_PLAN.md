# Show Commands Architecture Fix Plan

**Date:** 2026-02-18  
**Status:** READY FOR IMPLEMENTATION  
**Priority:** P0 - CRITICAL (Core functionality broken)  
**Estimated Effort:** 3-4 hours  

## Root Cause Analysis

### Issue 1: `orb requests show` Returns Generic Error
**Root Cause**: Command routing forces all single request queries through interface handler instead of CQRS
**Current Flow**: CLI → Interface Handler → Scheduler Strategy → Generic error message
**Expected Flow**: CLI → CQRS Query → GetRequestHandler → Proper RequestDTO response

### Issue 2: `orb machines show` Returns Request-Style Response  
**Root Cause**: Machine show command incorrectly routed through request status formatting
**Current Flow**: CLI → GetMachineQuery → GetMachineHandler → Request-style scheduler formatting
**Expected Flow**: CLI → GetMachineQuery → GetMachineHandler → Machine-specific formatting

## Architecture Analysis

### ✅ CQRS Infrastructure Working Correctly
- `GetRequestQuery` and `GetRequestHandler` work properly (tested with direct CQRS)
- `GetMachineQuery` and `GetMachineHandler` work properly (returns correct MachineDTO)
- Query handlers return proper DTOs with all required data

### ❌ CLI Routing Issues
1. **Request Show Routing**: Forces interface handler instead of CQRS for single requests
2. **Machine Show Formatting**: Uses request-style scheduler formatting instead of machine formatting
3. **Response Context**: Scheduler strategy doesn't distinguish between request and machine contexts

## Current vs Target Architecture

### Current (Broken) Flow

#### Request Show:
```
CLI args → Command Factory → None (forces interface handler)
→ Interface Handler → Scheduler Strategy → format_request_status_response()
→ Generic error message
```

#### Machine Show:
```  
CLI args → Command Factory → GetMachineQuery
→ GetMachineHandler → MachineDTO
→ Response Formatter → Scheduler Strategy → format_request_status_response()
→ Request-style response format
```

### Target (Fixed) Flow

#### Request Show:
```
CLI args → Command Factory → GetRequestQuery  
→ GetRequestHandler → RequestDTO
→ Response Formatter → format_request_details()
→ Proper request details
```

#### Machine Show:
```
CLI args → Command Factory → GetMachineQuery
→ GetMachineHandler → MachineDTO  
→ Response Formatter → format_machine_details()
→ Proper machine details
```

## Implementation Plan

### Phase 1: Fix Request Show Command Routing (1.5 hours)

#### 1.1 Update Command Factory to Use CQRS for Single Requests
**File:** `src/cli/command_factory.py`

**Problem**: Command factory returns `None` for single request show, forcing interface handler
**Solution**: Always return `GetRequestQuery` for single request show commands

```python
# Line 826 - BEFORE:
elif command_action == "status" or command_action == "show":
    # Check for --all flag first
    if args.get("all", False):
        return None  # Route to interface handler for --all support
    
    request_id = args.get("request_id")
    if not request_id:
        raise ValueError("request_id is required for status/show command")
    
    # If request_id is a list (multiple IDs), return None to handle in interface layer
    if isinstance(request_id, list):
        return None
    
    return self.create_get_request_status_query(
        request_id=request_id,
        provider_name=args.get("provider"),
        include_machines=True
    )

# AFTER: Distinguish between show and status commands
elif command_action == "show":
    # Show command: Always use CQRS for single request
    request_id = args.get("request_id")
    if not request_id:
        raise ValueError("request_id is required for show command")
    
    # Single request show: Use CQRS GetRequestQuery
    if not isinstance(request_id, list):
        return self.create_get_request_query(
            request_id=request_id,
            provider_name=args.get("provider"),
            long=True  # Show command should include full details
        )
    else:
        # Multiple IDs: Route to interface handler
        return None
        
elif command_action == "status":
    # Status command: Handle multiple IDs through interface handler
    if args.get("all", False):
        return None  # Route to interface handler for --all support
    
    request_id = args.get("request_id")
    if not request_id:
        raise ValueError("request_id is required for status command")
    
    # Always route status to interface handler for consistent multi-ID support
    return None
```

#### 1.2 Add Missing create_get_request_query Method
**File:** `src/cli/command_factory.py`

```python
def create_get_request_query(
    self,
    request_id: str,
    provider_name: Optional[str] = None,
    long: bool = False,
    lightweight: bool = False,
    **kwargs: Any,
) -> GetRequestQuery:
    """Create query to get single request details."""
    return GetRequestQuery(
        request_id=request_id,
        provider_name=provider_name,
        long=long,
        lightweight=lightweight
    )
```

### Phase 2: Add Machine-Specific Response Formatting (1.5 hours)

#### 2.1 Add Machine Details Formatting to Scheduler Strategy
**File:** `src/infrastructure/scheduler/hostfactory/hostfactory_strategy.py`

```python
def format_machine_details_response(self, machine: MachineDTO) -> dict[str, Any]:
    """
    Format single MachineDTO for show command response.
    Returns machine-specific details, not request-style format.
    """
    # Convert DTO to dict
    machine_dict = machine.to_dict()
    
    # Apply field mappings for HostFactory compatibility
    mapped_machine = self.field_mapper.map_fields(machine_dict)
    
    # Convert to camelCase for consistency
    camel_machine = self._convert_machine_to_camel(mapped_machine)
    
    return camel_machine

def format_machine_status_response(self, machines: list[MachineDTO]) -> dict[str, Any]:
    """
    Format multiple MachineDTO for status command response.
    Maintains existing behavior for status commands.
    """
    formatted_machines = []
    for machine_dto in machines:
        machine_dict = machine_dto.to_dict()
        mapped_machine = self.field_mapper.map_fields(machine_dict)
        camel_machine = self._convert_machine_to_camel(mapped_machine)
        formatted_machines.append(camel_machine)
    
    return {
        "machines": formatted_machines
    }
```

#### 2.2 Add Machine Details Formatting to Default Strategy
**File:** `src/infrastructure/scheduler/default/default_strategy.py`

```python
def format_machine_details_response(self, machine: MachineDTO) -> dict[str, Any]:
    """Format single MachineDTO for show command response."""
    return machine.to_dict()

def format_machine_status_response(self, machines: list[MachineDTO]) -> dict[str, Any]:
    """Format multiple MachineDTO for status command response."""
    return {
        "machines": [machine.to_dict() for machine in machines]
    }
```

#### 2.3 Add Methods to Scheduler Port Interface
**File:** `src/domain/base/ports/scheduler_port.py`

```python
@abstractmethod
def format_machine_details_response(self, machine: "MachineDTO") -> dict[str, Any]:
    """Format single machine details for show command."""

@abstractmethod  
def format_machine_status_response(self, machines: list["MachineDTO"]) -> dict[str, Any]:
    """Format multiple machine status for status command."""
```

### Phase 3: Update CLI Response Formatter (30 minutes)

#### 3.1 Add Context-Aware Formatting
**File:** `src/cli/response_formatter.py`

```python
def format_response(self, data: Any, args: Any) -> Union[str, tuple[str, int]]:
    """Format response with context awareness."""
    
    # Determine response context
    resource = getattr(args, 'resource', '')
    action = getattr(args, 'action', '')
    
    # Handle machine show specifically
    if resource == 'machines' and action == 'show':
        if isinstance(data, MachineDTO):
            # Single machine show: Use machine details formatting
            formatted_data = self.scheduler_strategy.format_machine_details_response(data)
            return self._format_output(formatted_data, args)
    
    # Handle machine status (multiple machines)
    elif resource == 'machines' and action == 'status':
        if isinstance(data, list) and all(isinstance(item, MachineDTO) for item in data):
            formatted_data = self.scheduler_strategy.format_machine_status_response(data)
            return self._format_output(formatted_data, args)
    
    # Handle request show specifically  
    elif resource == 'requests' and action == 'show':
        if isinstance(data, RequestDTO):
            # Single request show: Use existing request formatting but with proper context
            formatted_data = self.scheduler_strategy.format_request_status_response([data])
            # Extract single request from array response
            if 'requests' in formatted_data and formatted_data['requests']:
                return self._format_output(formatted_data['requests'][0], args)
            return self._format_output(formatted_data, args)
    
    # Existing logic for other cases...
    return self._format_existing_response(data, args)
```

### Phase 4: Update CLI Routing for Machine Show (30 minutes)

#### 4.1 Ensure Machine Show Uses CQRS Directly
**File:** `src/cli/main.py`

**Current routing forces machine show through interface handler. Update to use CQRS directly:**

```python
# In execute_command function, ensure machine show goes through CQRS:
# Machine show should NOT be routed to interface handler
# Command factory should return GetMachineQuery for single machine show
# Only machine status with multiple IDs should use interface handler
```

#### 4.2 Verify Command Factory Machine Show Logic
**File:** `src/cli/command_factory.py`

```python
# Line 903 - Ensure machine show returns GetMachineQuery:
elif command_action == "show":
    # Show command expects machine_id (singular)
    machine_id = args.get("machine_id") or args.get("flag_machine_id")
    if machine_id:
        return self.create_get_machine_query(
            machine_id=machine_id,
            provider_name=args.get("provider")
        )
    else:
        raise ValueError("machine_id is required for show command")
```

## Architecture Compliance

### ✅ Clean Architecture
- **Interface Layer**: CLI routing and response formatting
- **Application Layer**: CQRS queries and handlers  
- **Infrastructure Layer**: Scheduler strategy formatting
- **Domain Layer**: DTOs and business logic

### ✅ CQRS Pattern
- **Commands**: Not affected by this fix
- **Queries**: `GetRequestQuery` and `GetMachineQuery` used correctly
- **Handlers**: Existing handlers work properly, just need correct routing

### ✅ DDD Compliance
- **Aggregates**: Request and Machine aggregates unchanged
- **DTOs**: RequestDTO and MachineDTO provide proper data
- **Services**: No domain services affected

### ✅ SOLID Principles
- **SRP**: Each formatter handles single responsibility
- **OCP**: Easy to add new response formats without changing existing code
- **LSP**: All scheduler strategies implement same interface
- **ISP**: Focused interfaces for specific formatting operations
- **DIP**: CLI depends on scheduler abstractions

## Success Criteria

### Request Show Command
- ✅ `orb requests show req-uuid` returns detailed request information
- ✅ Shows request status, machines, error details, timestamps
- ✅ Uses proper CQRS flow through GetRequestHandler
- ✅ Returns structured data, not generic error message

### Machine Show Command  
- ✅ `orb machines show machine-id` returns detailed machine information
- ✅ Shows machine status, IPs, launch time, provider details
- ✅ Uses machine-specific formatting, not request-style format
- ✅ Returns single machine object, not request wrapper

### Architecture Quality
- ✅ Proper CQRS routing for single-entity show commands
- ✅ Context-aware response formatting
- ✅ Consistent behavior across scheduler strategies
- ✅ No duplication of existing functionality

## Files to Modify

### Core Changes
- `src/cli/command_factory.py` - Fix request show routing, add missing method
- `src/infrastructure/scheduler/hostfactory/hostfactory_strategy.py` - Add machine formatting
- `src/infrastructure/scheduler/default/default_strategy.py` - Add machine formatting  
- `src/domain/base/ports/scheduler_port.py` - Add interface methods
- `src/cli/response_formatter.py` - Add context-aware formatting

### Testing Required
- Test `orb requests show` with valid request ID
- Test `orb machines show` with valid machine ID
- Verify existing `orb requests status` and `orb machines status` still work
- Test error handling for invalid IDs

**Total Effort:** 3-4 hours  
**Priority:** P0 - CRITICAL (Core functionality broken)  
**Risk Level:** Low (Extends existing patterns, no breaking changes)

This plan fixes both show commands by ensuring proper CQRS routing and context-aware response formatting while maintaining all existing functionality.