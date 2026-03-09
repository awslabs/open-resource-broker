"""Consolidated response extraction helpers shared across all interface test files.

Each helper accepts both dict responses (CLI, REST, MCP) and object responses
(SDK DTOs), extracting the relevant field from whichever shape is present.
"""


def extract_request_id(result) -> str | None:
    """Extract request_id from any interface response shape."""
    if isinstance(result, dict):
        return (
            result.get("request_id") or result.get("requestId") or result.get("created_request_id")
        )
    return getattr(result, "request_id", None) or getattr(result, "created_request_id", None)


def extract_status(result) -> str:
    """Extract status string from any interface response shape."""
    if isinstance(result, dict):
        requests = result.get("requests", [])
        if requests and isinstance(requests[0], dict):
            return requests[0].get("status", "unknown")
        return result.get("status", "unknown")
    return getattr(result, "status", "unknown")


def extract_machine_ids(result) -> list[str]:
    """Extract machine ID list from any interface response shape."""
    if isinstance(result, dict):
        requests = result.get("requests", [])
        if requests and isinstance(requests[0], dict):
            machines = requests[0].get("machines", [])
            return [
                mid for m in machines for mid in [m.get("machineId") or m.get("machine_id")] if mid
            ]
        return []
    machines = getattr(result, "machines", [])
    return [str(mid) for m in machines for mid in [getattr(m, "machine_id", None)] if mid]
