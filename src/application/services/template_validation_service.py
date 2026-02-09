"""Generic template validation service."""

from domain.base.ports.logging_port import LoggingPort
from domain.template.template_aggregate import Template
from providers.results import ValidationResult


class TemplateValidationService:
    """Generic template validation service."""
    
    def __init__(self, logger: LoggingPort):
        self._logger = logger
    
    async def validate_template_requirements(
        self,
        template: Template,
        provider_instance: str
    ) -> ValidationResult:
        """Validate template against provider capabilities."""
        from providers.registry import get_provider_registry
        
        provider_registry = get_provider_registry()
        return provider_registry.validate_template_requirements(template, provider_instance)