"""Scheduler service registrations for dependency injection."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.di.container import DIContainer
    from infrastructure.scheduler.factory import SchedulerStrategyFactory


def register_scheduler_services(container: "DIContainer") -> None:
    """Register scheduler services with configuration-driven strategy loading."""
    
    # Lazy imports to avoid import cascade
    from infrastructure.scheduler.factory import SchedulerStrategyFactory

    # Register scheduler strategy factory
    container.register_factory(SchedulerStrategyFactory, create_scheduler_strategy_factory)

    # Register only the configured scheduler strategy
    _register_configured_scheduler_strategy(container)


def create_scheduler_strategy_factory(
    container: "DIContainer",
) -> "SchedulerStrategyFactory":
    """Create scheduler strategy factory with configuration."""
    from domain.base.ports import ConfigurationPort
    from infrastructure.scheduler.factory import SchedulerStrategyFactory
    
    config = container.get(ConfigurationPort)
    return SchedulerStrategyFactory(config_manager=config)


def _register_configured_scheduler_strategy(container: "DIContainer") -> None:
    """Register only the configured scheduler strategy."""
    from domain.base.ports import ConfigurationPort
    from infrastructure.logging.logger import get_logger
    from infrastructure.scheduler.registry import get_scheduler_registry
    
    try:
        config = container.get(ConfigurationPort)
        scheduler_type = config.get_scheduler_strategy()

        logger = get_logger(__name__)

        # Registry handles dynamic registration - no hardcoded types here
        registry = get_scheduler_registry()
        registry.ensure_type_registered(scheduler_type)

        logger.info("Registered configured scheduler strategy: %s", scheduler_type)

    except Exception as e:
        logger = get_logger(__name__)
        logger.error("Failed to register configured scheduler strategy: %s", e)
        # Fallback to default
        registry = get_scheduler_registry()
        registry.ensure_type_registered("default")
        logger.info("Registered fallback scheduler strategy: default")
