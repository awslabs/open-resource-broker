"""JSON template repository and strategy implementation."""

import json
import os
from typing import Any, Optional

from config.managers.configuration_manager import ConfigurationManager
from domain.base.exceptions import ConfigurationError
from domain.template.repository import TemplateRepository
from domain.template.template_aggregate import Template
from infrastructure.logging.logger import get_logger
from infrastructure.patterns.singleton_registry import SingletonRegistry
from infrastructure.persistence.base import StrategyBasedRepository
from infrastructure.persistence.json.provider_template_strategy import (
    ProviderTemplateStrategy,
)


class TemplateJSONRepository(StrategyBasedRepository, TemplateRepository):
    """JSON-based template repository with provider-specific file support."""

    def __init__(self, config_manager: ConfigurationManager) -> None:
        """
        Initialize template repository.

        Args:
            config_manager: Configuration manager
        """
        self.config_manager = config_manager
        self.logger = get_logger(__name__)

        # Try to inject metrics collector from DI container
        metrics = None
        try:
            from infrastructure.di.container import get_container
            from monitoring.metrics import MetricsCollector

            container = get_container()
            metrics = container.get_optional(MetricsCollector)
        except (AttributeError, ImportError):
            # Metrics collector not available, proceed without instrumentation
            # This is expected when metrics are disabled or during testing
            metrics = None

        # Use provider template strategy
        strategy = ProviderTemplateStrategy(
            config_manager=config_manager,
            create_dirs=True,
        )
        self.logger.info("Using provider-specific template loading strategy")

        super().__init__(strategy)

    def find_by_id(self, template_id: str) -> Optional[Template]:
        """
        Find template by ID.

        Args:
            template_id: Template ID

        Returns:
            Template aggregate if found, None otherwise
        """
        template_data = self.strategy.find_by_id(template_id)
        if template_data:
            try:
                return self._data_to_aggregate(template_data)
            except Exception as e:
                self.logger.error(
                    "Error converting template data to aggregate for '%s': %s",
                    template_id,
                    e,
                )
                return None
        return None

    def find_all(self) -> list[Template]:
        """
        Find all templates.

        Returns:
            List of all template aggregates
        """
        templates = []
        template_data_list = self.strategy.find_all()

        for template_data in template_data_list:
            try:
                template = self._data_to_aggregate(template_data)
                templates.append(template)
            except Exception as e:
                template_id = template_data.get("template_id", "unknown")
                self.logger.error(
                    "Error converting template data to aggregate for '%s': %s",
                    template_id,
                    e,
                )
                continue

        return templates

    def save(self, template: Template) -> None:
        """
        Save template.

        Args:
            template: Template aggregate to save
        """
        template_data = self._aggregate_to_data(template)
        self.strategy.save(template_data)

    def delete(self, template_id: str) -> bool:
        """
        Delete template by ID.

        Args:
            template_id: Template ID to delete

        Returns:
            True if template was deleted, False if not found
        """
        return self.strategy.delete(template_id)

    def find_by_provider_type(self, provider_type: str) -> list[Template]:
        """
        Find templates by provider type.

        Args:
            provider_type: Provider type to filter by

        Returns:
            List of templates for the specified provider type
        """
        all_templates = self.find_all()
        return [template for template in all_templates if template.provider_type == provider_type]

    def find_by_provider_name(self, provider_name: str) -> list[Template]:
        """
        Find templates by provider name/instance.

        Args:
            provider_name: Provider name/instance to filter by

        Returns:
            List of templates for the specified provider name
        """
        all_templates = self.find_all()
        return [template for template in all_templates if template.provider_name == provider_name]

    def get_template_source_info(self, template_id: str) -> Optional[dict[str, Any]]:
        """
        Get information about which file a template was loaded from.

        Args:
            template_id: Template ID

        Returns:
            Dictionary with source information or None if not found
        """
        if hasattr(self.strategy, "get_template_source_info"):
            return self.strategy.get_template_source_info(template_id)
        return None

    def refresh_templates(self) -> None:
        """Refresh template cache and file discovery."""
        if hasattr(self.strategy, "refresh_cache"):
            self.strategy.refresh_cache()
            self.logger.info("Refreshed template cache")

    def _data_to_aggregate(self, data: dict[str, Any]) -> Template:
        """
        Convert template data to Template aggregate.

        Args:
            data: Template data dictionary

        Returns:
            Template aggregate
        """
        # Extract required fields
        template_id = data.get("template_id")
        if not template_id:
            raise ValueError("Template data must include 'template_id'")

        image_id = data.get("image_id")
        if not image_id:
            raise ValueError(f"Template '{template_id}' must include 'image_id'")

        subnet_ids = data.get("subnet_ids", [])
        if not subnet_ids:
            raise ValueError(f"Template '{template_id}' must include 'subnet_ids'")

        max_instances = data.get("max_instances", 1)
        if max_instances <= 0:
            raise ValueError(f"Template '{template_id}' max_instances must be greater than 0")

        # Create Template aggregate with all fields
        return Template(
            template_id=template_id,
            provider_type=data.get("provider_type"),
            provider_name=data.get("provider_name"),
            provider_api=data.get("provider_api"),
            image_id=image_id,
            subnet_ids=subnet_ids,
            max_instances=max_instances,
            instance_type=data.get("instance_type"),
            key_name=data.get("key_name"),
            security_group_ids=data.get("security_group_ids", []),
            user_data=data.get("user_data"),
            price_type=data.get("price_type", "ondemand"),
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True),
        )

    def _aggregate_to_data(self, template: Template) -> dict[str, Any]:
        """
        Convert Template aggregate to data dictionary.

        Args:
            template: Template aggregate

        Returns:
            Template data dictionary
        """
        return {
            "template_id": template.template_id,
            "provider_type": template.provider_type,
            "provider_name": template.provider_name,
            "provider_api": template.provider_api,
            "image_id": template.image_id,
            "subnet_ids": template.subnet_ids,
            "max_instances": template.max_instances,
            "instance_type": template.instance_type,
            "key_name": template.key_name,
            "security_group_ids": template.security_group_ids,
            "user_data": template.user_data,
            "price_type": template.price_type,
            "metadata": template.metadata,
            "is_active": template.is_active,
        }


# Register the repository in the singleton registry
def get_template_repository(
    config_manager: ConfigurationManager = None,
) -> TemplateJSONRepository:
    """
    Get template repository instance.

    Args:
        config_manager: Configuration manager (required for first call)

    Returns:
        Template repository instance
    """
    registry = SingletonRegistry()

    if not registry.has("template_repository"):
        if not config_manager:
            raise ConfigurationError(
                "ConfigurationManager required for first template repository creation"
            )

        repository = TemplateJSONRepository(config_manager)
        registry.register("template_repository", repository)
        return repository

    return registry.get("template_repository")


# Legacy compatibility - keep the old class name
JSONTemplateRepositoryImpl = TemplateJSONRepository
