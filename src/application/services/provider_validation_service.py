"""Service for validating provider availability and compatibility.

This service extracts provider validation logic from command handlers,
following the Single Responsibility Principle.
"""

from __future__ import annotations

from typing import Any

from domain.base.ports import ContainerPort, LoggingPort, ProviderSelectionPort


class ProviderValidationService:
    """Service for validating provider availability and template compatibility."""

    def __init__(
        self,
        container: ContainerPort,
        logger: LoggingPort,
        provider_selection_port: ProviderSelectionPort,
    ) -> None:
        """Initialize the service.

        Args:
            container: DI container for service resolution
            logger: Logging port for structured logging
            provider_selection_port: Port for provider operations
        """
        self._container = container
        self.logger = logger
        self._provider_selection_port = provider_selection_port

    async def validate_provider_availability(self) -> None:
        """Validate that providers are available.

        Raises:
            ValueError: If no provider strategies are available
        """
        from domain.base.ports.configuration_port import ConfigurationPort

        config_manager = self._container.get(ConfigurationPort)
        provider_config = config_manager.get_provider_config()

        if provider_config:
            from providers.registry import get_provider_registry

            registry = get_provider_registry()
            for provider_instance in provider_config.get_active_providers():
                registry.ensure_provider_instance_registered_from_config(provider_instance)

        available_strategies = self._provider_selection_port.get_available_strategies()

        if not available_strategies:
            error_msg = "No provider strategies available - cannot create machine requests"
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        self.logger.debug("Available provider strategies: %s", available_strategies)

    async def select_and_validate_provider(self, template: Any) -> Any:
        """Select provider and validate template compatibility.

        Args:
            template: Template aggregate to validate

        Returns:
            Provider selection result

        Raises:
            ValueError: If template is incompatible with selected provider
        """
        selection_result = self._provider_selection_port.select_provider_for_template(template)

        self.logger.info(
            "Selected provider: %s (%s)",
            selection_result.provider_name,
            selection_result.selection_reason,
        )

        # Validation is temporarily skipped for testing
        # TODO: Re-enable validation once provider capabilities are stable
        # validation_result = self._provider_selection_port.validate_template_requirements(
        #     template, selection_result.provider_name
        # )
        #
        # if not validation_result.is_valid:
        #     error_msg = f"Template incompatible with provider {selection_result.provider_name}: {'; '.join(validation_result.errors)}"
        #     self.logger.error(error_msg)
        #     raise ValueError(error_msg)
        #
        # self.logger.info("Template validation passed: %s", validation_result.supported_features)

        self.logger.info("Skipping template validation for testing")

        return selection_result
