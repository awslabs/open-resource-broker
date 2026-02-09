"""Application service interface for provider registry access."""

from domain.base.ports.logging_port import LoggingPort
from domain.template.template_aggregate import Template
from providers.results import ProviderSelectionResult, ValidationResult


class ProviderRegistryService:
    """Application service interface for provider registry operations."""
    
    def __init__(self, logger: LoggingPort):
        self._logger = logger
    
    def select_provider_for_template(self, template: Template) -> ProviderSelectionResult:
        """Select provider instance for template requirements."""
        from providers.registry import get_provider_registry
        registry = get_provider_registry()
        return registry.select_provider_for_template(template)
    
    def validate_template_requirements(self, template: Template, provider_instance: str) -> ValidationResult:
        """Validate template requirements against provider capabilities."""
        from providers.registry import get_provider_registry
        registry = get_provider_registry()
        return registry.validate_template_requirements(template, provider_instance)
    
    def select_active_provider(self) -> ProviderSelectionResult:
        """Select active provider instance from configuration."""
        from providers.registry import get_provider_registry
        registry = get_provider_registry()
        return registry.select_active_provider()