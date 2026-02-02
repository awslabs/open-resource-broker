"""Provider service registrations for dependency injection."""

from application.services.provider_capability_service import ProviderCapabilityService
from application.services.provider_selection_service import ProviderSelectionService
from domain.base.ports import ConfigurationPort
from domain.base.ports.logging_port import LoggingPort
from infrastructure.di.container import DIContainer
from providers.factory import ProviderStrategyFactory
from infrastructure.logging.logger import get_logger
from providers.registry import ProviderRegistry
from providers.base.strategy import SelectorFactory


def register_provider_services(container: DIContainer) -> None:
    """Register provider application services and utilities."""

    # Register provider strategy factory
    container.register_factory(ProviderStrategyFactory, create_provider_strategy_factory)

    # Register SelectorFactory
    container.register_singleton(SelectorFactory, lambda c: SelectorFactory())

    # Register provider application services
    container.register_singleton(
        ProviderSelectionService,
        lambda c: ProviderSelectionService(
            config_manager=c.get(ConfigurationPort),
            logger=c.get(LoggingPort),
            provider_registry=None,  # Optional for now
        ),
    )

    container.register_singleton(
        ProviderCapabilityService,
        lambda c: ProviderCapabilityService(
            logger=c.get(LoggingPort), 
            config_manager=c.get(ConfigurationPort),
            provider_registry=c.get(ProviderRegistry)
        ),
    )

    # Register provider-specific utility services
    _register_provider_specific_services(container)

def create_provider_strategy_factory(container: DIContainer) -> ProviderStrategyFactory:
    """Create provider strategy factory."""
    return ProviderStrategyFactory(
        logger=container.get(LoggingPort), config_manager=container.get(ConfigurationPort)
    )


def _register_provider_specific_services(container: DIContainer) -> None:
    """Register provider-specific utility services."""
    logger = get_logger(__name__)

    # Register AWS utility services if available
    try:
        import importlib.util

        # Check if AWS provider is available
        if importlib.util.find_spec("src.providers.aws"):
            try:
                from providers.aws.registration import register_aws_services_with_di
                register_aws_services_with_di(container)
            except Exception as e:
                logger.warning("Failed to register AWS services with DI: %s", str(e))
                logger.debug("Continuing without AWS services registration")

            # Register core AWS utility services (adapters, operations)
            try:
                _register_aws_utility_services(container)
            except Exception as e:
                logger.warning("Failed to register core AWS utility services: %s", str(e))
                logger.debug("Continuing without core AWS utility services registration")
        else:
            logger.debug("AWS provider not available, skipping AWS service registration")
    except ImportError:
        logger.debug("AWS provider not available, skipping AWS service registration")
    except Exception as e:
        logger.warning("Failed to register AWS services: %s", str(e))


def _register_aws_utility_services(container: DIContainer) -> None:
    """Register AWS utility services (adapters, operations, etc.)."""
    logger = get_logger(__name__)

    try:
        # Import AWS utility classes
        try:
            from providers.aws.utilities.aws_operations import AWSOperations
            from providers.aws.infrastructure.adapters.template_adapter import AWSTemplateAdapter
            from providers.aws.infrastructure.adapters.machine_adapter import AWSMachineAdapter
            from providers.aws.infrastructure.adapters.aws_provisioning_adapter import AWSProvisioningAdapter
            from providers.aws.infrastructure.adapters.request_adapter import AWSRequestAdapter
            from providers.aws.infrastructure.adapters.resource_manager_adapter import AWSResourceManagerAdapter
            from providers.aws.strategy.aws_provider_adapter import AWSProviderAdapter
            from providers.aws.managers.aws_instance_manager import AWSInstanceManager
            from providers.aws.managers.aws_resource_manager import AWSResourceManagerImpl
            
            from infrastructure.adapters.ports.cloud_resource_manager_port import CloudResourceManagerPort
            from infrastructure.adapters.ports.request_adapter_port import RequestAdapterPort
            from infrastructure.adapters.ports.resource_provisioning_port import ResourceProvisioningPort
        except Exception as e:
            logger.debug("Failed to import AWS utility classes: %s", e)
            raise

        # Register utility services
        container.register_singleton(AWSOperations)
        container.register_singleton(AWSTemplateAdapter)
        container.register_singleton(AWSMachineAdapter)
        container.register_singleton(AWSProvisioningAdapter)
        container.register_singleton(AWSRequestAdapter)
        container.register_singleton(AWSResourceManagerAdapter)
        container.register_singleton(AWSProviderAdapter)
        container.register_singleton(AWSInstanceManager)
        container.register_singleton(AWSResourceManagerImpl)

        # Register port implementations
        container.register_factory(ResourceProvisioningPort, lambda c: c.get(AWSProvisioningAdapter))
        container.register_factory(CloudResourceManagerPort, lambda c: c.get(AWSResourceManagerAdapter))
        container.register_factory(RequestAdapterPort, lambda c: c.get(AWSRequestAdapter))

        logger.info("AWS utility services registered successfully")
    except ImportError as e:
        logger.warning("Failed to import AWS utility classes: %s", str(e))
    except Exception as e:
        logger.warning("Failed to register AWS utility services: %s", str(e))


