"""Timestamp utilities for consistent formatting across the application."""

from datetime import datetime, timezone
from typing import Union


def to_iso_timestamp(dt: Union[datetime, float, int, None]) -> str | None:
    """
    Convert any timestamp format to ISO format with UTC timezone.
    
    Args:
        dt: Datetime object, unix timestamp (int/float), or None
        
    Returns:
        ISO format timestamp string with UTC timezone or None
    """
    if dt is None:
        return None
        
    if isinstance(dt, (int, float)):
        dt = datetime.fromtimestamp(dt, tz=timezone.utc)
    elif isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    else:
        return None
        
    return dt.isoformat()


def now_iso() -> str:
    """Get current timestamp in ISO format with UTC timezone."""
    return datetime.now(timezone.utc).isoformat()
