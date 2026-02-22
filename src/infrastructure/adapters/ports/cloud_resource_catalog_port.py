"""Cloud resource catalog port - focused interface for resource catalog operations."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CloudResourceCatalogPort(ABC):
    """Focused port for cloud resource catalog operations.

    This interface follows ISP by providing only catalog-related operations,
    allowing clients that only need resource type and pricing information to depend on a minimal interface.
    """

    @abstractmethod
    def get_resource_types(self) -> list[str]:
        """Get a list of available resource types.

        Returns:
            List of resource type identifiers

        Raises:
            InfrastructureError: For infrastructure errors
        """

    @abstractmethod
    def get_resource_pricing(
        self, resource_type: str, region: Optional[str] = None
    ) -> dict[str, Any]:
        """Get pricing information for a specific resource type.

        Args:
            resource_type: Type of resource (e.g., 'instances', 'volumes')
            region: Optional region to get pricing for

        Returns:
            Dictionary containing pricing information

        Raises:
            InfrastructureError: For infrastructure errors
        """
