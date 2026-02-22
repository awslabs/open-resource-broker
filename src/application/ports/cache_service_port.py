"""Cache service port interface."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CacheServicePort(ABC):
    """Port interface for cache service operations.

    This port defines the contract for caching operations in the application layer.
    Infrastructure adapters must implement this interface to provide caching functionality.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (optional)
        """
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete value from cache.

        Args:
            key: Cache key
        """
        ...

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        ...
