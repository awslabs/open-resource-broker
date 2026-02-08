"""Template Generation Service - Application Layer."""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json
from datetime import datetime

from domain.base.ports import ConfigurationPort, LoggingPort, SchedulerPort
from domain.template.template_aggregate import Template
from application.dto.template_generation_dto import (
    TemplateGenerationRequest,
    TemplateGenerationResult,
    ProviderTemplateResult
)


class TemplateGenerationService:
    """
    Application service for template generation.
    
    Handles template generation business logic while maintaining proper
    layer separation and dependency injection.
    """

    def __init__(
        self,
        config_manager: ConfigurationPort,
        scheduler_strategy: SchedulerPort,
        logger: LoggingPort,
    ):
        self._config_manager = config_manager
        self._scheduler_strategy = scheduler_strategy
        self._logger = logger

    async def generate_templates(self, request: TemplateGenerationRequest) -> TemplateGenerationResult:
        """
        Generate templates based on request parameters.
        
        Args:
            request: Template generation request with provider selection and options
            
        Returns:
            TemplateGenerationResult with generation status and results
        """
        try:
            # Determine target providers
            providers = self._determine_target_providers(request)
            
            # Generate templates for each provider
            results = []
            for provider in providers:
                result = await self._generate_templates_for_provider(provider, request)
                results.append(result)
            
            # Calculate summary
            created_results = [r for r in results if r.status == "created"]
            skipped_results = [r for r in results if r.status == "skipped"]
            total_templates = sum(r.templates_count for r in created_results)
            
            return TemplateGenerationResult(
                status="success",
                message=f"Generated templates for {len(results)} providers",
                providers=results,
                total_templates=total_templates,
                created_count=len(created_results),
                skipped_count=len(skipped_results)
            )
            
        except Exception as e:
            self._logger.error("Template generation failed: %s", str(e))
            return TemplateGenerationResult(
                status="error",
                message=f"Failed to generate templates: {e}",
                providers=[],
                total_templates=0,
                created_count=0,
                skipped_count=0
            )

    def _determine_target_providers(self, request: TemplateGenerationRequest) -> List[Dict[str, str]]:
        """Determine which providers to generate templates for."""
        if request.specific_provider:
            return [self._get_provider_config(request.specific_provider)]
        elif request.all_providers:
            return self._get_active_providers()
        else:
            # Default: generate for all active providers
            return self._get_active_providers()

    async def _generate_templates_for_provider(
        self, 
        provider: Dict[str, str], 
        request: TemplateGenerationRequest
    ) -> ProviderTemplateResult:
        """Generate templates for a single provider."""
        provider_name = provider["name"]
        provider_type = provider["type"]
        
        try:
            # Generate example templates using provider registry
            examples = await self._generate_examples_from_provider(
                provider_type, 
                provider_name, 
                request.provider_api
            )
            
            # Determine output filename
            filename = self._determine_filename(provider, request)
            
            # Check for existing file
            templates_file = self._get_templates_file_path(filename)
            if templates_file.exists() and not request.force_overwrite:
                return ProviderTemplateResult(
                    provider=provider_name,
                    filename=filename,
                    templates_count=0,
                    path=str(templates_file),
                    status="skipped",
                    reason="file_exists"
                )
            
            # Format templates using scheduler strategy
            formatted_examples = self._format_templates(examples, request)
            
            # Write templates file
            self._write_templates_file(templates_file, formatted_examples)
            
            return ProviderTemplateResult(
                provider=provider_name,
                filename=filename,
                templates_count=len(examples),
                path=str(templates_file),
                status="created"
            )
            
        except Exception as e:
            self._logger.error("Failed to generate templates for provider %s: %s", provider_name, str(e))
            return ProviderTemplateResult(
                provider=provider_name,
                filename="",
                templates_count=0,
                path="",
                status="error",
                reason=str(e)
            )

    async def _generate_examples_from_provider(
        self, 
        provider_type: str, 
        provider_name: str, 
        provider_api: Optional[str] = None
    ) -> List[Template]:
        """Generate example templates using provider registry."""
        from providers.registry import get_provider_registry
        from infrastructure.di.container import get_container
        
        registry = get_provider_registry()
        container = get_container()
        
        # Ensure provider type is registered
        if not registry.is_provider_registered(provider_type):
            registry.ensure_provider_type_registered(provider_type)
        
        if not registry.is_provider_registered(provider_type):
            error_msg = registry.format_registry_error(provider_type, "provider")
            raise ValueError(error_msg)
        
        # For AWS provider, use the existing handler factory
        if provider_type == "aws":
            from providers.aws.infrastructure.aws_handler_factory import AWSHandlerFactory
            
            handler_factory = container.get(AWSHandlerFactory)
            if not handler_factory:
                raise ValueError(f"AWSHandlerFactory not available for provider: {provider_name}")
            
            # Generate example templates
            example_templates = handler_factory.generate_example_templates()
            if not example_templates:
                raise ValueError(f"No example templates generated for provider: {provider_name}")
            
            # Filter by provider_api if specified
            if provider_api:
                example_templates = [
                    template for template in example_templates 
                    if template.provider_api == provider_api
                ]
                if not example_templates:
                    raise ValueError(f"No templates found for provider API: {provider_api}")
            
            return example_templates
        else:
            # For other providers, return empty list for now
            return []

    def _determine_filename(self, provider: Dict[str, str], request: TemplateGenerationRequest) -> str:
        """Determine the output filename based on generation mode."""
        provider_name = provider["name"]
        provider_type = provider["type"]
        
        if request.provider_specific:
            # Provider-specific mode: use provider name pattern
            config_dict = self._get_config_dict()
            return self._scheduler_strategy.get_templates_filename(provider_name, provider_type, config_dict)
        elif request.provider_type_filter:
            # Provider-type mode: use specified provider type
            return f"{request.provider_type_filter}_templates.json"
        else:
            # Generic mode: use provider_type pattern
            return f"{provider_type}_templates.json"

    def _format_templates(self, examples: List[Template], request: TemplateGenerationRequest) -> List[Dict[str, Any]]:
        """Format templates using scheduler strategy."""
        # Convert Template objects to dict format
        template_dicts = []
        for template in examples:
            template_dict = template.model_dump(exclude_none=True, mode='json')
            template_dicts.append(template_dict)
        
        # Apply scheduler formatting
        return self._scheduler_strategy.format_templates_for_generation(template_dicts)

    def _get_templates_file_path(self, filename: str) -> Path:
        """Get the full path for templates file."""
        from config.platform_dirs import get_config_location
        
        config_dir = get_config_location()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / filename

    def _write_templates_file(self, templates_file: Path, formatted_examples: List[Dict[str, Any]]) -> None:
        """Write templates to file with proper JSON encoding."""
        templates_data = {"templates": formatted_examples}
        
        class DateTimeEncoder(json.JSONEncoder):
            def default(self, obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                try:
                    return super().default(obj)
                except TypeError:
                    return str(obj)
        
        with open(templates_file, "w") as f:
            json.dump(templates_data, f, indent=2, cls=DateTimeEncoder)

    def _get_active_providers(self) -> List[Dict[str, str]]:
        """Get all active providers from configuration."""
        config_dict = self._get_config_dict()
        
        if not config_dict:
            # Fallback to provider registry
            return self._get_providers_from_registry()
        
        provider_config = config_dict.get("provider", {})
        providers = provider_config.get("providers", [])
        
        # Return enabled providers
        active_providers = []
        for provider in providers:
            if provider.get("enabled", True):
                active_providers.append({"name": provider["name"], "type": provider["type"]})
        
        # Fallback if no providers configured
        if not active_providers:
            return self._get_providers_from_registry()
        
        return active_providers

    def _get_provider_config(self, provider_name: str) -> Dict[str, str]:
        """Get configuration for specific provider."""
        config_dict = self._get_config_dict()
        
        if not config_dict:
            # Fallback for specific provider
            return {
                "name": provider_name,
                "type": provider_name.split("-")[0] if "-" in provider_name else provider_name,
            }
        
        provider_config = config_dict.get("provider", {})
        providers = provider_config.get("providers", [])
        
        # Find specific provider
        for provider in providers:
            if provider["name"] == provider_name:
                return {"name": provider["name"], "type": provider["type"]}
        
        # Provider not found, create from name
        return {
            "name": provider_name,
            "type": provider_name.split("-")[0] if "-" in provider_name else provider_name,
        }

    def _get_config_dict(self) -> Optional[Dict[str, Any]]:
        """Get configuration dictionary from file."""
        from config.platform_dirs import get_config_location
        
        config_dir = get_config_location()
        config_file = config_dir / "config.json"
        
        if not config_file.exists():
            return None
        
        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception as e:
            self._logger.warning("Failed to load config file: %s", str(e))
            return None

    def _get_providers_from_registry(self) -> List[Dict[str, str]]:
        """Fallback to get providers from registry."""
        try:
            from providers.registry import get_provider_registry
            from domain.base.ports import ConfigurationPort, LoggingPort
            from infrastructure.metrics.collector import MetricsCollector
            from infrastructure.di.container import get_container
            
            registry = get_provider_registry()
            
            # Ensure dependencies are set
            if not registry._provider_config:
                container = get_container()
                logger = container.get(LoggingPort)
                config_manager = container.get(ConfigurationPort)
                metrics = container.get(MetricsCollector)
                registry.set_dependencies(logger, config_manager, metrics)
            
            selection_result = registry.select_active_provider()
            return [{"name": selection_result.provider_instance, "type": selection_result.provider_type}]
        except Exception:
            # Final fallback
            from providers.registry import get_provider_registry
            registry = get_provider_registry()
            registered_types = registry.get_registered_providers()
            default_type = registered_types[0] if registered_types else "aws"
            return [{"name": "default", "type": default_type}]