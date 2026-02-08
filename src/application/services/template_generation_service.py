"""Template generation application service."""

from typing import Any, Dict, List, Optional
from pathlib import Path
import json

from domain.base.ports.configuration_port import ConfigurationPort
from domain.base.ports.logging_port import LoggingPort
from domain.base.ports.scheduler_port import SchedulerPort
from providers.registry import get_provider_registry
from infrastructure.di.container import get_container


class TemplateGenerationService:
    """Application service for template generation operations."""

    def __init__(
        self,
        config_manager: ConfigurationPort,
        scheduler_strategy: SchedulerPort,
        logger: LoggingPort,
    ):
        self._config_manager = config_manager
        self._scheduler_strategy = scheduler_strategy
        self._logger = logger

    async def generate_templates(
        self,
        provider_name: Optional[str] = None,
        all_providers: bool = False,
        provider_api: Optional[str] = None,
        provider_specific: bool = False,
        provider_type: Optional[str] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Generate templates based on specified parameters."""
        try:
            # Determine providers to generate for
            if provider_name:
                providers = [self._get_provider_config(provider_name)]
            elif all_providers:
                providers = self._get_active_providers()
            else:
                providers = self._get_active_providers()

            results = []
            skipped_files = []

            for provider in providers:
                result = await self._generate_templates_for_provider(
                    provider, provider_api, provider_specific, provider_type, force
                )
                results.append(result)

                if result.get("status") == "skipped":
                    skipped_files.append(result["filename"])

            created_results = [r for r in results if r.get("status") == "created"]
            total_templates = sum(r["templates_count"] for r in created_results)

            return {
                "status": "success",
                "message": f"Generated templates for {len(results)} providers",
                "providers": results,
                "total_templates": total_templates,
                "skipped_files": skipped_files,
                "created_count": len(created_results),
            }

        except Exception as e:
            self._logger.error(f"Template generation failed: {e}")
            return {
                "status": "error",
                "message": f"Failed to generate templates: {e}",
            }

    async def _generate_templates_for_provider(
        self,
        provider: dict,
        provider_api: Optional[str],
        provider_specific: bool,
        provider_type: Optional[str],
        force: bool,
    ) -> dict:
        """Generate templates for a single provider."""
        provider_name = provider["name"]
        provider_type_actual = provider["type"]

        # Generate examples using provider registry
        examples = await self._generate_examples_from_registry(
            provider_type_actual, provider_name, provider_api
        )

        # Determine filename
        filename = self._determine_filename(
            provider_name, provider_type_actual, provider_specific, provider_type
        )

        # Get templates directory
        templates_dir = self._get_templates_directory()
        templates_file = templates_dir / filename

        # Check for existing file
        if templates_file.exists() and not force:
            return {
                "provider": provider_name,
                "filename": filename,
                "templates_count": 0,
                "path": str(templates_file),
                "status": "skipped",
                "reason": "file_exists",
            }

        # Format templates
        formatted_examples = self._scheduler_strategy.format_templates_for_generation(examples)

        # Write templates file
        self._write_templates_file(templates_file, formatted_examples)

        return {
            "provider": provider_name,
            "filename": filename,
            "templates_count": len(examples),
            "path": str(templates_file),
            "status": "created",
        }

    async def _generate_examples_from_registry(
        self, provider_type: str, provider_name: str, provider_api: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Generate example templates using provider registry."""
        registry = get_provider_registry()

        # Ensure provider type is registered
        if not registry.is_provider_registered(provider_type):
            registry.ensure_provider_type_registered(provider_type)

        if not registry.is_provider_registered(provider_type):
            error_msg = registry.format_registry_error(provider_type, "provider")
            raise ValueError(error_msg)

        # For AWS provider
        if provider_type == "aws":
            from providers.aws.infrastructure.aws_handler_factory import AWSHandlerFactory

            container = get_container()
            handler_factory = container.get(AWSHandlerFactory)
            if not handler_factory:
                raise ValueError(f"AWSHandlerFactory not available for provider: {provider_name}")

            example_templates = handler_factory.generate_example_templates()
            if not example_templates:
                raise ValueError(f"No example templates generated for provider: {provider_name}")

            # Filter by provider_api if specified
            if provider_api:
                example_templates = [
                    template
                    for template in example_templates
                    if template.provider_api == provider_api
                ]
                if not example_templates:
                    raise ValueError(f"No templates found for provider API: {provider_api}")

            # Convert Template objects to dict format
            examples = []
            for template in example_templates:
                template_dict = template.model_dump(exclude_none=True, mode="json")
                examples.append(template_dict)

            return examples
        else:
            # For other providers, return empty list
            return []

    def _determine_filename(
        self,
        provider_name: str,
        provider_type: str,
        provider_specific: bool,
        provider_type_arg: Optional[str],
    ) -> str:
        """Determine the filename for generated templates."""
        if provider_specific:
            # Provider-specific mode: use scheduler strategy
            config_dict = self._get_config_dict()
            return self._scheduler_strategy.get_templates_filename(
                provider_name, provider_type, config_dict
            )
        elif provider_type_arg:
            # Provider-type mode: use specified provider type
            return f"{provider_type_arg}_templates.json"
        else:
            # Generic mode: use provider_type pattern
            return f"{provider_type}_templates.json"

    def _get_templates_directory(self) -> Path:
        """Get the templates directory."""
        from config.platform_dirs import get_config_location

        config_dir = get_config_location()
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def _write_templates_file(self, templates_file: Path, formatted_examples: List[Dict[str, Any]]) -> None:
        """Write templates to file."""
        templates_data = {"templates": formatted_examples}

        # Write JSON with datetime handling
        from datetime import datetime

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

    def _get_active_providers(self) -> List[dict]:
        """Get all active providers from configuration."""
        config_dict = self._get_config_dict()
        if not config_dict:
            return self._get_fallback_providers()

        provider_config = config_dict.get("provider", {})
        providers = provider_config.get("providers", [])

        # Return enabled providers
        active_providers = []
        for provider in providers:
            if provider.get("enabled", True):
                active_providers.append({"name": provider["name"], "type": provider["type"]})

        return active_providers if active_providers else self._get_fallback_providers()

    def _get_provider_config(self, provider_name: str) -> dict:
        """Get configuration for specific provider."""
        config_dict = self._get_config_dict()
        if not config_dict:
            return self._create_provider_config_from_name(provider_name)

        provider_config = config_dict.get("provider", {})
        providers = provider_config.get("providers", [])

        # Find specific provider
        for provider in providers:
            if provider["name"] == provider_name:
                return {"name": provider["name"], "type": provider["type"]}

        return self._create_provider_config_from_name(provider_name)

    def _get_config_dict(self) -> Optional[dict]:
        """Get configuration dictionary."""
        from config.platform_dirs import get_config_location

        config_dir = get_config_location()
        config_file = config_dir / "config.json"

        if not config_file.exists():
            return None

        try:
            with open(config_file) as f:
                return json.load(f)
        except Exception:
            return None

    def _get_fallback_providers(self) -> List[dict]:
        """Get fallback providers when no configuration exists."""
        try:
            registry = get_provider_registry()
            
            # Ensure dependencies are set
            if not registry._provider_config:
                container = get_container()
                logger = container.get(LoggingPort)
                config_manager = container.get(ConfigurationPort)
                from infrastructure.metrics.collector import MetricsCollector
                metrics = container.get(MetricsCollector)
                registry.set_dependencies(logger, config_manager, metrics)

            selection_result = registry.select_active_provider()
            return [{"name": selection_result.provider_instance, "type": selection_result.provider_type}]
        except Exception:
            # Final fallback
            registry = get_provider_registry()
            registered_types = registry.get_registered_providers()
            default_type = registered_types[0] if registered_types else "aws"
            return [{"name": "default", "type": default_type}]

    def _create_provider_config_from_name(self, provider_name: str) -> dict:
        """Create provider config from name."""
        return {
            "name": provider_name,
            "type": provider_name.split("-")[0] if "-" in provider_name else provider_name,
        }