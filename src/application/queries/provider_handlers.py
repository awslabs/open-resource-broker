"""Provider Strategy Query Handlers - CQRS handlers for provider strategy queries.

This module implements query handlers for retrieving provider strategy information,
leveraging the Provider Registry for clean CQRS interfaces.
"""

import time
from typing import Any, cast

from application.base.handlers import BaseQueryHandler
from application.decorators import query_handler
from application.dto.system import (
    ProviderCapabilitiesDTO,
    ProviderHealthDTO,
    ProviderStrategyConfigDTO,
)
from application.provider.queries import (
    GetProviderCapabilitiesQuery,
    GetProviderHealthQuery,
    GetProviderMetricsQuery,
    GetProviderStrategyConfigQuery,
    ListAvailableProvidersQuery,
)
from application.services.provider_registry_service import ProviderRegistryService
from domain.base.ports import ConfigurationPort, ErrorHandlingPort, LoggingPort
from domain.services.generic_filter_service import GenericFilterService
from domain.services.timestamp_service import TimestampService


@query_handler(GetProviderHealthQuery)  # type: ignore[arg-type]
class GetProviderHealthHandler(BaseQueryHandler[GetProviderHealthQuery, dict[str, Any]]):
    """Handler for retrieving provider health status."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
        timestamp_service: TimestampService,
        provider_registry_service: ProviderRegistryService,
    ) -> None:
        """
        Initialize provider health handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
            timestamp_service: Service for timestamp formatting
            provider_registry_service: Service for provider registry operations
        """
        super().__init__(logger, error_handler)
        self.timestamp_service = timestamp_service
        self._provider_registry_service = provider_registry_service

    async def execute_query(self, query: GetProviderHealthQuery) -> dict[str, Any]:
        """Execute provider health query."""
        self.logger.info("Getting health for provider: %s", query.provider_name)

        try:
            # If no provider specified, get the active provider
            provider_name = query.provider_name
            if not provider_name:
                try:
                    selection_result = self._provider_registry_service.select_active_provider()
                    provider_name = selection_result.provider_name
                    self.logger.debug("Using active provider: %s", provider_name)
                except Exception as e:
                    self.logger.warning("Failed to get active provider: %s", e, exc_info=True)
                    return {
                        "provider_name": None,
                        "status": "not_found",
                        "health": "unknown",
                        "message": "No active provider found",
                    }

            # Get health information from registry service
            health_status = self._provider_registry_service.check_strategy_health(provider_name)

            health_info = {
                "provider_name": provider_name,
                "status": "active",
                "health": "healthy" if health_status and health_status.is_healthy else "unhealthy",
                "last_check": self.timestamp_service.current_timestamp(),
                "message": getattr(health_status, "message", None)
                or getattr(health_status, "error_message", None)
                or "No health data available",
            }

            if health_status:
                health_info.update(
                    {
                        "details": getattr(health_status, "details", {}),
                        "timestamp": self.timestamp_service.format_for_display(
                            getattr(health_status, "timestamp", time.time())
                        ),
                    }
                )
            else:
                health_info["timestamp"] = self.timestamp_service.current_timestamp()

            self.logger.info("Provider %s health: %s", provider_name, health_info["health"])
            return health_info

        except Exception as e:
            self.logger.error("Failed to get provider health: %s", e, exc_info=True)
            return {
                "provider_name": query.provider_name,
                "status": "error",
                "health": "unhealthy",
                "message": str(e),
            }


@query_handler(ListAvailableProvidersQuery)  # type: ignore[arg-type]
class ListAvailableProvidersHandler(BaseQueryHandler[ListAvailableProvidersQuery, dict[str, Any]]):
    """Handler for listing available providers."""

    def __init__(
        self,
        config_manager: ConfigurationPort,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
        generic_filter_service: GenericFilterService,
    ) -> None:
        """
        Initialize list providers handler.

        Args:
            config_manager: Configuration port for getting provider config
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
            generic_filter_service: Service for applying generic filters
        """
        super().__init__(logger, error_handler)
        self._config_manager = config_manager
        self._generic_filter_service = generic_filter_service

    async def execute_query(self, query: ListAvailableProvidersQuery) -> dict[str, Any]:
        """Execute list available providers query."""
        self.logger.info("Listing available providers")

        try:
            # Get configured providers from configuration (not registry)
            # Cast to Any since ConfigurationPort.get_provider_config() returns dict[str, Any]
            # but the actual runtime object has richer methods
            provider_config: Any = cast(Any, self._config_manager.get_provider_config())

            if not provider_config:
                return {
                    "providers": [],
                    "count": 0,
                    "message": "No provider configuration found",
                }

            # Get active providers from configuration
            active_providers = provider_config.get_active_providers()

            # Filter by provider name if specified (restore lost functionality)
            if query.provider_name:
                active_providers = [p for p in active_providers if p.name == query.provider_name]
                if not active_providers:
                    return {
                        "providers": [],
                        "count": 0,
                        "message": f"Provider '{query.provider_name}' not found in configuration",
                    }

            providers_info = []
            for provider_instance in active_providers:
                # Get effective handlers using inheritance
                provider_defaults = provider_config.provider_defaults.get(provider_instance.type)
                effective_handlers = provider_instance.get_effective_handlers(provider_defaults)
                handler_names = list(effective_handlers.keys())

                providers_info.append(
                    {
                        "name": provider_instance.name,
                        "type": provider_instance.type,
                        "region": provider_instance.config.get("region", "unknown"),
                        "status": "active" if provider_instance.enabled else "disabled",
                        "capabilities": handler_names,  # Real handler names from inheritance
                        "weight": provider_instance.weight,
                        "priority": provider_instance.priority,
                    }
                )

            # Apply generic filters if provided
            if query.filter_expressions:
                providers_info = self._generic_filter_service.apply_filters(
                    providers_info, query.filter_expressions
                )

            return {
                "providers": providers_info,
                "count": len(providers_info),
                "selection_policy": provider_config.selection_policy,
                "message": "Available providers retrieved successfully",
            }

        except Exception as e:
            self.logger.error("Failed to list available providers: %s", e, exc_info=True)
            return {
                "providers": [],
                "count": 0,
                "message": f"Failed to retrieve providers: {e}",
            }


@query_handler(GetProviderCapabilitiesQuery)  # type: ignore[arg-type]
class GetProviderCapabilitiesHandler(
    BaseQueryHandler[GetProviderCapabilitiesQuery, dict[str, Any]]
):
    """Handler for retrieving provider capabilities."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
        provider_registry_service: ProviderRegistryService,
    ) -> None:
        """
        Initialize provider capabilities handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
            provider_registry_service: Service for provider registry operations
        """
        super().__init__(logger, error_handler)
        self._provider_registry_service = provider_registry_service

    async def execute_query(self, query: GetProviderCapabilitiesQuery) -> dict[str, Any]:
        """Execute provider capabilities query."""
        self.logger.info("Getting capabilities for provider: %s", query.provider_name)

        try:
            # Get capabilities from registry service
            capabilities_obj = self._provider_registry_service.get_strategy_capabilities(
                query.provider_name
            )

            capabilities = {
                "provider_name": query.provider_name,
                "capabilities": capabilities_obj.supported_apis if capabilities_obj else [],
                "supported_operations": capabilities_obj.supported_operations
                if capabilities_obj
                else [],
                "features": capabilities_obj.features if capabilities_obj else {},
            }

            self.logger.info("Retrieved capabilities for provider: %s", query.provider_name)
            return capabilities

        except Exception as e:
            self.logger.error("Failed to get provider capabilities: %s", e, exc_info=True)
            raise


@query_handler(GetProviderMetricsQuery)  # type: ignore[arg-type]
class GetProviderMetricsHandler(BaseQueryHandler[GetProviderMetricsQuery, dict[str, Any]]):
    """Handler for retrieving provider metrics."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
        timestamp_service: TimestampService,
        provider_registry_service: ProviderRegistryService,
    ) -> None:
        """
        Initialize provider metrics handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
            timestamp_service: Service for timestamp formatting
            provider_registry_service: Service for provider registry operations
        """
        super().__init__(logger, error_handler)
        self.timestamp_service = timestamp_service
        self._provider_registry_service = provider_registry_service

    async def execute_query(self, query: GetProviderMetricsQuery) -> dict[str, Any]:
        """Execute provider metrics query."""
        self.logger.info("Getting metrics for provider: %s", query.provider_name)

        try:
            # Get basic metrics (registry doesn't store detailed metrics)

            metrics = {
                "provider_name": query.provider_name,
                "timestamp": self.timestamp_service.current_timestamp(),
                "status": "active",
                "registered_at": "unknown",  # Registry doesn't track registration time
            }

            self.logger.info("Retrieved metrics for provider: %s", query.provider_name)
            return metrics

        except Exception as e:
            self.logger.error("Failed to get provider metrics: %s", e, exc_info=True)
            raise


@query_handler(GetProviderStrategyConfigQuery)  # type: ignore[arg-type]
class GetProviderStrategyConfigHandler(
    BaseQueryHandler[GetProviderStrategyConfigQuery, dict[str, Any]]
):
    """Handler for retrieving provider strategy configuration."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
        provider_registry_service: ProviderRegistryService,
    ) -> None:
        """
        Initialize provider strategy config handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
            provider_registry_service: Service for provider registry operations
        """
        super().__init__(logger, error_handler)
        self._provider_registry_service = provider_registry_service

    async def execute_query(self, query: GetProviderStrategyConfigQuery) -> dict[str, Any]:
        """Execute provider strategy configuration query."""
        self.logger.info("Getting strategy config for provider")

        try:
            # Get basic configuration info
            config = {
                "strategy_type": "registry_managed",
                "is_registered": True,
            }

            self.logger.info("Retrieved strategy config for provider")
            return config

        except Exception as e:
            self.logger.error("Failed to get provider strategy config: %s", e, exc_info=True)
            raise
