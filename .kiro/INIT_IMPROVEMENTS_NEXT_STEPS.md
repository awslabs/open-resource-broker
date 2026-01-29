# Init Command Improvements - Next Steps

**Date:** 2026-01-29  
**Status:** TODO - Ready for Implementation  
**Priority:** P1 - HIGH (Core functionality improvements)

## Current Issues

### 1. Template Generation Returns 0 Templates
**Problem:** `orb templates generate` creates 0 templates
**Root Cause:** Using CQRS QueryBus to get existing templates, but no templates exist yet
**Expected:** Should generate example templates from provider handlers

### 2. Hardcoded Schedulers in Init
**Problem:** Schedulers hardcoded in init command
```python
# Current (hardcoded):
print_info("  (1) default    - Standalone usage")
print_info("  (2) hostfactory - IBM Spectrum Symphony integration")
```
**Expected:** Get schedulers from registry/strategy

### 3. Hardcoded Providers in Init  
**Problem:** Providers hardcoded in init command
```python
# Current (hardcoded):
print_info("  (1) aws - Amazon Web Services")
```
**Expected:** Get providers from registry/strategy

### 4. AWS Profiles Not Listed
**Problem:** User must manually type AWS profile name
**Expected:** Read from `~/.aws/config` and `~/.aws/credentials` and list available profiles

## Implementation Plan

### Phase 1: Fix Template Generation (HIGH PRIORITY)
**Issue:** Template generation returns 0 templates instead of creating examples

**Root Cause Analysis:**
- Current code uses `ListTemplatesQuery` to get existing templates
- But we want to generate NEW example templates, not list existing ones
- Should use provider strategy's `handler_factory.generate_example_templates()`

**Fix:**
```python
# Instead of querying existing templates:
templates = await query_bus.execute(ListTemplatesQuery(...))

# Generate new example templates:
strategy = get_provider_strategy(provider_name)
templates = strategy.handler_factory.generate_example_templates()
```

**Files to modify:**
- `src/interface/templates_generate_handler.py`

### Phase 2: Dynamic Scheduler Discovery
**Goal:** Get schedulers from registry instead of hardcoding

**Implementation:**
```python
def _get_available_schedulers() -> list[dict]:
    """Get available schedulers from registry."""
    from infrastructure.scheduler.registry import get_scheduler_registry
    
    registry = get_scheduler_registry()
    schedulers = []
    
    for name, info in registry.get_available_schedulers().items():
        schedulers.append({
            "name": name,
            "display_name": info.get("display_name", name),
            "description": info.get("description", "")
        })
    
    return schedulers

# Usage in init:
schedulers = _get_available_schedulers()
for i, scheduler in enumerate(schedulers, 1):
    print_info(f"  ({i}) {scheduler['display_name']} - {scheduler['description']}")
```

**Files to modify:**
- `src/interface/init_command_handler.py`
- May need to create scheduler registry if doesn't exist

### Phase 3: Dynamic Provider Discovery
**Goal:** Get providers from registry instead of hardcoding

**Implementation:**
```python
def _get_available_providers() -> list[dict]:
    """Get available providers from registry."""
    from infrastructure.di.container import get_container
    from application.services.provider_selection_service import ProviderSelectionService
    
    container = get_container()
    provider_service = container.get(ProviderSelectionService)
    
    return provider_service.get_available_providers()

# Usage in init:
providers = _get_available_providers()
for i, provider in enumerate(providers, 1):
    print_info(f"  ({i}) {provider['type']} - {provider['description']}")
```

**Files to modify:**
- `src/interface/init_command_handler.py`

### Phase 4: AWS Profile Discovery
**Goal:** Read and list AWS profiles from local config

**Implementation:**
```python
def _get_aws_profiles() -> list[str]:
    """Get AWS profiles from ~/.aws/config and ~/.aws/credentials."""
    import configparser
    from pathlib import Path
    
    profiles = set()
    
    # Read from ~/.aws/credentials
    creds_file = Path.home() / ".aws" / "credentials"
    if creds_file.exists():
        config = configparser.ConfigParser()
        config.read(creds_file)
        profiles.update(config.sections())
    
    # Read from ~/.aws/config
    config_file = Path.home() / ".aws" / "config"
    if config_file.exists():
        config = configparser.ConfigParser()
        config.read(config_file)
        for section in config.sections():
            if section.startswith("profile "):
                profiles.add(section[8:])  # Remove "profile " prefix
            elif section == "default":
                profiles.add("default")
    
    return sorted(list(profiles))

# Usage in init:
if provider_type == "aws":
    profiles = _get_aws_profiles()
    if profiles:
        print_info("Available profiles:")
        for i, profile in enumerate(profiles, 1):
            print_info(f"  ({i}) {profile}")
        print_info("  (c) Custom profile name")
        
        profile_choice = input("  Select profile (1): ").strip() or "1"
        if profile_choice.lower() == 'c':
            profile = input("  Enter profile name: ").strip()
        else:
            try:
                profile = profiles[int(profile_choice) - 1]
            except (ValueError, IndexError):
                profile = "default"
    else:
        profile = input("  Profile (default): ").strip() or "default"
```

**Files to modify:**
- `src/interface/init_command_handler.py`

## Success Criteria

### Phase 1 Complete:
- ✅ `orb templates generate` creates actual example templates (not 0)
- ✅ Templates are written to files
- ✅ Templates contain valid AWS infrastructure examples

### Phase 2 Complete:
- ✅ Schedulers discovered dynamically from registry
- ✅ No hardcoded scheduler list in init command
- ✅ New schedulers automatically appear in init

### Phase 3 Complete:
- ✅ Providers discovered dynamically from registry
- ✅ No hardcoded provider list in init command
- ✅ New providers automatically appear in init

### Phase 4 Complete:
- ✅ AWS profiles read from local config files
- ✅ User can select from available profiles
- ✅ Fallback to manual entry if no profiles found

## Estimated Effort

- **Phase 1 (Template Generation):** 2-3 hours
- **Phase 2 (Scheduler Discovery):** 3-4 hours  
- **Phase 3 (Provider Discovery):** 2-3 hours
- **Phase 4 (AWS Profile Discovery):** 2-3 hours
- **Total:** 9-13 hours

## Files to Modify

### High Priority:
- `src/interface/templates_generate_handler.py` - Fix template generation
- `src/interface/init_command_handler.py` - Dynamic discovery

### May Need Creation:
- Scheduler registry (if doesn't exist)
- Provider registry enhancements

---

**Ready for implementation - Phase 1 should be tackled first as it's blocking template generation functionality.**
