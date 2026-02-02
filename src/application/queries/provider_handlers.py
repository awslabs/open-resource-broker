"""Provider Strategy Query Handlers - CQRS handlers for provider strategy queries.

This module implements query handlers for retrieving provider strategy information,
leveraging the Provider Registry for clean CQRS interfaces.
"""

import time
from typing import Any

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
from domain.base.ports import ErrorHandlingPort, LoggingPort


@query_handler(GetProviderHealthQuery)
class GetProviderHealthHandler(BaseQueryHandler[GetProviderHealthQuery, ProviderHealthDTO]):
    """Handler for retrieving provider health status."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
    ) -> None:
        """
        Initialize provider health handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
        """
        super().__init__(logger, error_handler)

    async def execute_query(self, query: GetProviderHealthQuery) -> dict[str, Any]:
        """Execute provider health query."""
        self.logger.info("Getting health for provider: %s", query.provider_name)

        try:
            from providers.registry import get_provider_registry
            registry = get_provider_registry()

            # Check if provider exists
            if not (registry.is_provider_registered(query.provider_name) or 
                   registry.is_provider_instance_registered(query.provider_name)):
                return {
                    "provider_name": query.provider_name,
                    "status": "not_found",
                    "health": "unknown",
                    "message": f"Provider '{query.provider_name}' not found",
                }

            # Get health information from registry
            health_status = registry.check_strategy_health(query.provider_name)
            
            health_info = {
                "provider_name": query.provider_name,
                "status": "active",
                "health": "healthy" if health_status and health_status.is_healthy else "unhealthy",
                "last_check": time.time(),
                "message": health_status.message if health_status else "No health data available",
            }

            if health_status:
                health_info.update({
                    "details": health_status.details,
                    "timestamp": health_status.timestamp,
                })

            self.logger.info("Provider %s health: %s", query.provider_name, health_info["health"])
            return health_info

        except Exception as e:
            self.logger.error("Failed to get provider health: %s", e)
            return {
                "provider_name": query.provider_name,
                "status": "error",
                "health": "unhealthy",
                "message": str(e),
            }


@query_handler(ListAvailableProvidersQuery)
class ListAvailableProvidersHandler(
    BaseQueryHandler[ListAvailableProvidersQuery, list[dict[str, Any]]]
):
    """Handler for listing available providers."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
    ) -> None:
        """
        Initialize list providers handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
        """
        super().__init__(logger, error_handler)

    async def execute_query(self, query: ListAvailableProvidersQuery) -> list[dict[str, Any]]:
        """Execute list available providers query."""
        self.logger.info("Listing available providers")

        try:
            from providers.registry import get_provider_registry
            registry = get_provider_registry()

            available_providers = []

            # Get provider types and instances
            provider_types = registry.get_registered_providers()
            provider_instances = registry.get_registered_provider_instances()

            # Add provider types
            for provider_type in provider_types:
                try:
                    capabilities = registry.get_strategy_capabilities(provider_type)
                    provider_info = {
                        "name": provider_type,
                        "type": provider_type,
                        "status": "active",
                        "capabilities": capabilities.supported_apis if capabilities else [],
                    }
                    available_providers.append(provider_info)
                except Exception as e:
                    self.logger.warning("Could not get info for provider type %s: %s", provider_type, e)
                    available_providers.append(
                        {
                            "name": provider_type,
                            "type": provider_type,
                            "status": "error",
                            "error": str(e),
                        }
                    )

            # Add provider instances
            for instance_name in provider_instances:
                try:
                    capabilities = registry.get_strategy_capabilities(instance_name)
                    provider_info = {
                        "name": instance_name,
                        "type": "instance",
                        "status": "active",
                        "capabilities": capabilities.supported_apis if capabilities else [],
                    }
                    available_providers.append(provider_info)
                except Exception as e:
                    self.logger.warning("Could not get info for provider instance %s: %s", instance_name, e)
                    available_providers.append(
                        {
                            "name": instance_name,
                            "type": "instance",
                            "status": "error",
                            "error": str(e),
                        }
                    )

            self.logger.info("Found %s available providers", len(available_providers))
            return available_providers

        except Exception as e:
            self.logger.error("Failed to list available providers: %s", e)
            raise


@query_handler(GetProviderCapabilitiesQuery)
class GetProviderCapabilitiesHandler(
    BaseQueryHandler[GetProviderCapabilitiesQuery, ProviderCapabilitiesDTO]
):
    """Handler for retrieving provider capabilities."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
    ) -> None:
        """
        Initialize provider capabilities handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
        """
        super().__init__(logger, error_handler)

    async def execute_query(self, query: GetProviderCapabilitiesQuery) -> dict[str, Any]:
        """Execute provider capabilities query."""
        self.logger.info("Getting capabilities for provider: %s", query.provider_name)

        try:
            from providers.registry import get_provider_registry
            registry = get_provider_registry()

            # Check if provider exists
            if not (registry.is_provider_registered(query.provider_name) or 
                   registry.is_provider_instance_registered(query.provider_name)):
                return {
                    "provider_name": query.provider_name,
                    "capabilities": [],
                    "error": f"Provider '{query.provider_name}' not found",
                }

            # Get capabilities from registry
            capabilities_obj = registry.get_strategy_capabilities(query.provider_name)
            
            capabilities = {
                "provider_name": query.provider_name,
                "capabilities": capabilities_obj.supported_apis if capabilities_obj else [],
                "supported_operations": capabilities_obj.supported_operations if capabilities_obj else [],
                "features": capabilities_obj.features if capabilities_obj else {},
            }

            self.logger.info("Retrieved capabilities for provider: %s", query.provider_name)
            return capabilities

        except Exception as e:
            self.logger.error("Failed to get provider capabilities: %s", e)
            raise


@query_handler(GetProviderMetricsQuery)
class GetProviderMetricsHandler(BaseQueryHandler[GetProviderMetricsQuery, dict[str, Any]]):
    """Handler for retrieving provider metrics."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
    ) -> None:
        """
        Initialize provider metrics handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
        """
        super().__init__(logger, error_handler)

    async def execute_query(self, query: GetProviderMetricsQuery) -> dict[str, Any]:
        """Execute provider metrics query."""
        self.logger.info("Getting metrics for provider: %s", query.provider_name)

        try:
            from providers.registry import get_provider_registry
            registry = get_provider_registry()

            # Check if provider exists
            if not (registry.is_provider_registered(query.provider_name) or 
                   registry.is_provider_instance_registered(query.provider_name)):
                return {
                    "provider_name": query.provider_name,
                    "metrics": {},
                    "error": f"Provider '{query.provider_name}' not found",
                }

            # Get basic metrics (registry doesn't store detailed metrics)
            metrics = {
                "provider_name": query.provider_name,
                "timestamp": time.time(),
                "status": "active",
                "registered_at": "unknown",  # Registry doesn't track registration time
            }

            self.logger.info("Retrieved metrics for provider: %s", query.provider_name)
            return metrics

        except Exception as e:
            self.logger.error("Failed to get provider metrics: %s", e)
            raise


@query_handler(GetProviderStrategyConfigQuery)
class GetProviderStrategyConfigHandler(
    BaseQueryHandler[GetProviderStrategyConfigQuery, ProviderStrategyConfigDTO]
):
    """Handler for retrieving provider strategy configuration."""

    def __init__(
        self,
        logger: LoggingPort,
        error_handler: ErrorHandlingPort,
    ) -> None:
        """
        Initialize provider strategy config handler.

        Args:
            logger: Logging port for operation logging
            error_handler: Error handling port for exception management
        """
        super().__init__(logger, error_handler)

    async def execute_query(self, query: GetProviderStrategyConfigQuery) -> dict[str, Any]:
        """Execute provider strategy configuration query."""
        self.logger.info("Getting strategy config for provider: %s", query.provider_name)

        try:
            from providers.registry import get_provider_registry
            registry = get_provider_registry()

            # Check if provider exists
            if not (registry.is_provider_registered(query.provider_name) or 
                   registry.is_provider_instance_registered(query.provider_name)):
                return {
                    "provider_name": query.provider_name,
                    "configuration": {},
                    "error": f"Provider '{query.provider_name}' not found",
                }

            # Get basic configuration info
            config = {
                "provider_name": query.provider_name,
                "strategy_type": "registry_managed",
                "is_registered": True,
                "is_instance": registry.is_provider_instance_registered(query.provider_name),
            }

            self.logger.info("Retrieved strategy config for provider: %s", query.provider_name)
            return config

        except Exception as e:
            self.logger.error("Failed to get provider strategy config: %s", e)
            raise
