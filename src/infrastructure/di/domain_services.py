"""Domain services registration for dependency injection container."""

from domain.base.ports.configuration_port import ConfigurationPort
from domain.base.ports.logging_port import LoggingPort
from domain.services.filter_service import FilterService
from domain.services.generic_filter_service import GenericFilterService
from domain.services.template_validation_domain_service import TemplateValidationDomainService
from domain.services.timestamp_service import TimestampService
from infrastructure.di.container import DIContainer
from infrastructure.services.iso_timestamp_service import ISOTimestampService
from infrastructure.services.machine_filter_service import MachineFilterService


def register_domain_services(container: DIContainer) -> None:
    """Register domain services in the DI container."""

    # Template validation domain service - lazy initialization
    def create_template_validation_service(c):
        service = TemplateValidationDomainService()
        # Inject dependencies after creation
        config = c.get(ConfigurationPort)
        logger = c.get(LoggingPort)
        service.inject_dependencies(config, logger)
        return service

    container.register_singleton(
        TemplateValidationDomainService, create_template_validation_service
    )

    # Timestamp service
    container.register_singleton(TimestampService, lambda c: ISOTimestampService())

    # Filter service
    container.register_singleton(FilterService, lambda c: MachineFilterService())

    # Generic filter service
    container.register_singleton(GenericFilterService, lambda c: GenericFilterService())
