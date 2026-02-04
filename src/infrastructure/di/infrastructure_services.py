"""Infrastructure service registrations for dependency injection."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.di.container import DIContainer


def register_infrastructure_services(container: "DIContainer") -> None:
    """Register infrastructure services."""
    _register_template_services(container)
    _register_repository_services(container)


def _register_template_services(container: "DIContainer") -> None:
    """Register template configuration services."""

    def create_template_defaults_service(c: "DIContainer"):
        """Create template defaults service with injected dependencies."""
        from application.services.template_defaults_service import TemplateDefaultsService
        from domain.base.ports.configuration_port import ConfigurationPort
        from domain.base.ports.logging_port import LoggingPort

        return TemplateDefaultsService(
            config_manager=c.get(ConfigurationPort),
            logger=c.get(LoggingPort),
        )

    def create_template_configuration_manager(container: "DIContainer"):
        """Create template configuration manager with dependencies."""
        from infrastructure.template.configuration_manager import TemplateConfigurationManager
        from domain.base.ports.scheduler_port import SchedulerPort
        from domain.base.ports.configuration_port import ConfigurationPort
        from domain.base.ports.logging_port import LoggingPort
        from domain.template.ports.template_defaults_port import TemplateDefaultsPort

        return TemplateConfigurationManager(
            config_manager=container.get(ConfigurationPort),
            scheduler_strategy=container.get(SchedulerPort),
            logger=container.get(LoggingPort),
            event_publisher=None,
            provider_capability_service=None,
            template_defaults_service=container.get(TemplateDefaultsPort),
        )

    from domain.template.ports.template_defaults_port import TemplateDefaultsPort
    from infrastructure.template.configuration_manager import TemplateConfigurationManager

    container.register_singleton(TemplateDefaultsPort, create_template_defaults_service)
    container.register_singleton(TemplateConfigurationManager, create_template_configuration_manager)


def _register_repository_services(container: "DIContainer") -> None:
    """Register repository services."""

    def create_template_repository(container: "DIContainer"):
        """Create TemplateRepository."""
        from infrastructure.template.template_repository_impl import create_template_repository_impl
        from infrastructure.template.configuration_manager import TemplateConfigurationManager
        from domain.base.ports.logging_port import LoggingPort

        return create_template_repository_impl(
            template_manager=container.get(TemplateConfigurationManager),
            logger=container.get(LoggingPort),
        )

    from infrastructure.utilities.factories.repository_factory import RepositoryFactory
    from domain.machine.repository import MachineRepository
    from domain.request.repository import RequestRepository
    from domain.template.repository import TemplateRepository

    container.register_singleton(RepositoryFactory)
    container.register_singleton(
        RequestRepository,
        lambda c: c.get(RepositoryFactory).create_request_repository(),
    )
    container.register_singleton(
        MachineRepository,
        lambda c: c.get(RepositoryFactory).create_machine_repository(),
    )
    container.register_singleton(TemplateRepository, create_template_repository)
