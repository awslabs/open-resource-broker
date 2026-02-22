"""Cloud resource quota port - focused interface for quota operations."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CloudResourceQuotaPort(ABC):
    """Focused port for cloud resource quota operations.

    This interface follows ISP by providing only quota-related operations,
    allowing clients that only need quota information to depend on a minimal interface.
    """

    @abstractmethod
    def get_resource_quota(
        self, resource_type: str, region: Optional[str] = None
    ) -> dict[str, Any]:
        """Get quota information for a specific resource type.

        Args:
            resource_type: Type of resource (e.g., 'instances', 'volumes')
            region: Optional region to check quotas for

        Returns:
            Dictionary containing quota information

        Raises:
            InfrastructureError: For infrastructure errors
        """

    @abstractmethod
    def check_resource_availability(
        self, resource_type: str, count: int, region: Optional[str] = None
    ) -> bool:
        """Check if the requested number of resources are available.

        Args:
            resource_type: Type of resource (e.g., 'instances', 'volumes')
            count: Number of resources to check
            region: Optional region to check availability for

        Returns:
            True if resources are available, False otherwise

        Raises:
            InfrastructureError: For infrastructure errors
        """
