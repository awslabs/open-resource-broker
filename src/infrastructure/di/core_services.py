"""Core service registrations for dependency injection."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.di.container import DIContainer


def register_core_services(container: "DIContainer") -> None:
    """Register core application services."""

    # ConfigurationManager is now registered earlier in lazy mode
    # Only register it here if not already registered (eager mode)
    def check_configuration_manager():
        from config.managers.configuration_manager import ConfigurationManager
        return container.has(ConfigurationManager)
    
    if not check_configuration_manager():
        def create_configuration_manager(c):
            from config.managers.configuration_manager import ConfigurationManager
            return ConfigurationManager()  # Uses default config discovery
        
        container.register_singleton(ConfigurationManager, create_configuration_manager)

    # Register metrics collector with configuration from ConfigurationPort
    def create_metrics_collector(c):
        from domain.base.ports import ConfigurationPort
        from monitoring.metrics import MetricsCollector
        config_port = c.get(ConfigurationPort)
        metrics_config = config_port.get_metrics_config()
        return MetricsCollector(metrics_config)

    # Register as singleton so the same collector instance is shared
    def register_metrics_collector():
        from monitoring.metrics import MetricsCollector
        container.register_singleton(MetricsCollector, create_metrics_collector)
    
    register_metrics_collector()

    # Register factories
    def create_scheduler_factory(c):
        from config.managers.configuration_manager import ConfigurationManager
        from infrastructure.scheduler.factory import SchedulerStrategyFactory
        return SchedulerStrategyFactory(c.get(ConfigurationManager))
    
    def create_storage_factory(c):
        from config.managers.configuration_manager import ConfigurationManager
        from infrastructure.storage.factory import StorageStrategyFactory
        return StorageStrategyFactory(c.get(ConfigurationManager))
    
    def register_factories():
        from infrastructure.scheduler.factory import SchedulerStrategyFactory
        from infrastructure.storage.factory import StorageStrategyFactory
        container.register_factory(SchedulerStrategyFactory, create_scheduler_factory)
        container.register_factory(StorageStrategyFactory, create_storage_factory)
    
    register_factories()

    # Register scheduler strategy
    def register_scheduler_port():
        from domain.base.ports import SchedulerPort
        container.register_factory(SchedulerPort, lambda c: _create_scheduler_strategy(c))
    
    register_scheduler_port()

    # Register storage strategy
    def register_storage_port():
        from domain.base.ports import StoragePort
        container.register_factory(StoragePort, lambda c: _create_storage_strategy(c))
    
    register_storage_port()

    # Register provider strategy
    def register_provider_port():
        from domain.base.ports import ProviderPort
        container.register_factory(ProviderPort, lambda c: _create_provider_strategy(c))
    
    register_provider_port()

    # Register event publisher
    def create_event_publisher(c):
        from infrastructure.events.publisher import ConfigurableEventPublisher
        return ConfigurableEventPublisher(mode="logging")  # Default to logging mode

    def register_event_publisher():
        from domain.base.ports import EventPublisherPort
        container.register_factory(EventPublisherPort, create_event_publisher)
    
    register_event_publisher()

    # Register command and query buses conditionally based on lazy loading mode
    # If lazy loading is enabled, buses will be registered by CQRS handler discovery
    # If lazy loading is disabled, register them as factories immediately
    if not container.is_lazy_loading_enabled():
        def create_command_bus(c):
            from domain.base.ports import LoggingPort
            from infrastructure.di.buses import CommandBus
            return CommandBus(container=c, logger=c.get(LoggingPort))
        
        def create_query_bus(c):
            from domain.base.ports import LoggingPort
            from infrastructure.di.buses import QueryBus
            return QueryBus(container=c, logger=c.get(LoggingPort))
        
        def register_buses():
            from infrastructure.di.buses import CommandBus, QueryBus
            container.register_factory(CommandBus, create_command_bus)
            container.register_factory(QueryBus, create_query_bus)
        
        register_buses()

    # Register native spec service
    def create_native_spec_service(c):
        """Create native spec service."""
        from application.services.native_spec_service import NativeSpecService
        from domain.base.ports import ConfigurationPort
        from domain.base.ports.spec_rendering_port import SpecRenderingPort

        return NativeSpecService(
            config_port=c.get(ConfigurationPort), spec_renderer=c.get(SpecRenderingPort)
        )

    def register_native_spec_service():
        from application.services.native_spec_service import NativeSpecService
        container.register_factory(NativeSpecService, create_native_spec_service)
    
    register_native_spec_service()


def _create_scheduler_strategy(container: "DIContainer") -> "SchedulerPort":
    """Create scheduler strategy using factory."""
    from domain.base.ports import ConfigurationPort, SchedulerPort
    from infrastructure.scheduler.factory import SchedulerStrategyFactory

    factory = container.get(SchedulerStrategyFactory)
    config = container.get(ConfigurationPort)
    scheduler_type = config.get_scheduler_strategy()
    return factory.create_strategy(scheduler_type, container)


def _create_storage_strategy(container: "DIContainer") -> "StoragePort":
    """Create storage strategy using factory."""
    from domain.base.ports import ConfigurationPort, StoragePort
    from infrastructure.storage.factory import StorageStrategyFactory

    factory = container.get(StorageStrategyFactory)
    config = container.get(ConfigurationPort)
    storage_type = config.get_storage_strategy()
    return factory.create_strategy(storage_type, config)


def _create_provider_strategy(container: "DIContainer") -> "ProviderPort":
    """Create provider strategy using registry pattern."""
    from domain.base.ports import LoggingPort, ProviderPort
    from infrastructure.adapters.provider_registry_adapter import ProviderRegistryAdapter
    from monitoring.metrics import MetricsCollector
    from providers.registry import get_provider_registry

    registry = get_provider_registry()
    logger = container.get(LoggingPort)
    metrics = container.get(MetricsCollector)
    registry.set_dependencies(logger, metrics)
    return ProviderRegistryAdapter(registry)
