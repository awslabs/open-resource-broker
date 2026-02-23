"""
Cloud Resource Manager Port

This module defines the composite interface for managing cloud resources.
It follows the Port-Adapter pattern from Hexagonal Architecture (Ports and Adapters).

This is a composite interface that combines focused cloud resource interfaces.
Clients should depend on the specific focused interfaces they need rather than this fat interface.
"""

from abc import ABC

from .cloud_account_port import CloudAccountPort
from .cloud_resource_catalog_port import CloudResourceCatalogPort
from .cloud_resource_quota_port import CloudResourceQuotaPort


class CloudResourceManagerPort(
    CloudResourceQuotaPort, CloudResourceCatalogPort, CloudAccountPort, ABC
):
    """Composite interface for managing cloud resources.

    This interface is provided for backward compatibility and for implementations
    that need all cloud resource operations. New code should depend on the focused interfaces:
    - CloudResourceQuotaPort: For quota and availability checks
    - CloudResourceCatalogPort: For resource types and pricing
    - CloudAccountPort: For account information and credential validation

    This follows ISP by allowing clients to depend on minimal interfaces.
    """

    pass
