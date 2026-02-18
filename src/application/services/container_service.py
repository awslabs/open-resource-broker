"""Container service for application layer DI container access."""

from typing import Any, Optional

from domain.base.ports.logging_port import LoggingPort


class ContainerService:
    """Application service interface for DI container access."""

    def __init__(self, logger: LoggingPort):
        self._logger = logger

    def get_service(self, service_type: str) -> Any:
        """Get service from DI container."""
        from infrastructure.di.container import get_container

        container = get_container()
        return container.get(service_type)

    def get_optional_service(self, service_type: str) -> Optional[Any]:
        """Get optional service from DI container."""
        from infrastructure.di.container import get_container

        container = get_container()
        return container.get_optional(service_type)
