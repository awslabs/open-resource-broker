# Host Factory Supported APIs

This document outlines all AWS provider APIs supported by Host Factory, and current implementation status.


## Supported API Combinations

### Current Implementation Status

| Provider API | Fleet Type | Price Type | Status | Description |
|-------------|------------|------------|---------|-------------|
| **RunInstances** | - | ondemand | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **RunInstances** | - | spot | <span style="color: red; font-weight: bold;">NOT-SUPPORT</span> | Intentionally not supported to maintain backward compatibility |
|||||
| **SpotFleet** | request | ondemand | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **SpotFleet** | request | spot | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
|||||
| **EC2Fleet** | instant | ondemand | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **EC2Fleet** | instant | spot | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **EC2Fleet** | request | ondemand |<span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **EC2Fleet** | request | spot | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **EC2Fleet** | maintain | ondemand |<span style="color: orange; font-weight: bold;">NOT-IMPLEMENTED</span> |  |
| **EC2Fleet** | maintain | spot | <span style="color: orange; font-weight: bold;">NOT-IMPLEMENTED</span> |  |
|||||
| **ASG** | - | ondemand | <span style="color: blue; font-weight: bold;">IMPLEMENTED</span> |  |
| **ASG** | - | spot | <span style="color: orange; font-weight: bold;">NOT-IMPLEMENTED</span> |  |



### Legend

- <span style="color: blue; font-weight: bold;">IMPLEMENTED</span>: Code implemented and tested.
- <span style="color: orange; font-weight: bold;">NOT-IMPLEMENTED</span>: Not yet implemented.
- <span style="color: red; font-weight: bold;">NOT-SUPPORT</span>: Intentionally not supported.



