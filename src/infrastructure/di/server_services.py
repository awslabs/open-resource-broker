"""Server service registrations for dependency injection."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from infrastructure.di.container import DIContainer


def register_server_services(container: "DIContainer") -> None:
    """
    Register server services conditionally based on configuration.

    Only registers server components if server.enabled=true in configuration.
    This follows the established pattern of conditional service registration.

    Args:
        container: DI container instance
    """
    from config.schemas.server_schema import ServerConfig
    from domain.base.ports.configuration_port import ConfigurationPort
    from infrastructure.logging.logger import get_logger
    
    logger = get_logger(__name__)
    try:
        config_manager = container.get(ConfigurationPort)
        server_config = config_manager.get_typed(ServerConfig)

        if server_config.enabled:
            logger.info("Server enabled - registering FastAPI services")
            _register_fastapi_services(container, server_config)
            _register_api_handlers(container)
            logger.info("FastAPI services registered successfully")
        else:
            logger.debug("Server disabled - skipping FastAPI service registration")

    except Exception as e:
        logger.warning("Failed to register server services: %s", e)


def _register_fastapi_services(container: "DIContainer", server_config) -> None:
    """Register FastAPI core services."""
    from fastapi import FastAPI
    from api.server import create_fastapi_app
    from config.schemas.server_schema import ServerConfig

    container.register_singleton(FastAPI, lambda c: create_fastapi_app(server_config))
    container.register_singleton(ServerConfig, lambda c: server_config)


def _register_api_handlers(container: "DIContainer") -> None:
    """Register API handlers with dependency injection."""
    from infrastructure.logging.logger import get_logger
    
    logger = get_logger(__name__)
    
    try:
        from api.handlers.get_available_templates_handler import GetAvailableTemplatesRESTHandler
        from domain.base.ports import SchedulerPort
        from infrastructure.di.buses import CommandBus, QueryBus
        from monitoring.metrics import MetricsCollector

        if not container.is_registered(GetAvailableTemplatesRESTHandler):
            container.register_singleton(
                GetAvailableTemplatesRESTHandler,
                lambda c: GetAvailableTemplatesRESTHandler(
                    query_bus=c.get(QueryBus),
                    command_bus=c.get(CommandBus),
                    scheduler_strategy=c.get(SchedulerPort),
                    metrics=(
                        c.get(MetricsCollector) if c.is_registered(MetricsCollector) else None
                    ),
                ),
            )
    except ImportError:
        logger.debug("Template handler not available for registration")

    try:
        from api.handlers.request_machines_handler import RequestMachinesRESTHandler
        from domain.base.ports import SchedulerPort, ErrorHandlingPort
        from domain.base.ports.logging_port import LoggingPort
        from infrastructure.di.buses import CommandBus, QueryBus
        from monitoring.metrics import MetricsCollector

        if not container.is_registered(RequestMachinesRESTHandler):
            container.register_singleton(
                RequestMachinesRESTHandler,
                lambda c: RequestMachinesRESTHandler(
                    query_bus=c.get(QueryBus),
                    command_bus=c.get(CommandBus),
                    scheduler_strategy=c.get(SchedulerPort),
                    logger=c.get(LoggingPort),
                    error_handler=(
                        c.get(ErrorHandlingPort) if c.is_registered(ErrorHandlingPort) else None
                    ),
                    metrics=(
                        c.get(MetricsCollector) if c.is_registered(MetricsCollector) else None
                    ),
                ),
            )
    except ImportError:
        logger.debug("Request machines handler not available for registration")

    try:
        from api.handlers.get_request_status_handler import GetRequestStatusRESTHandler
        from domain.base.ports import SchedulerPort, ErrorHandlingPort
        from domain.base.ports.logging_port import LoggingPort
        from infrastructure.di.buses import CommandBus, QueryBus
        from monitoring.metrics import MetricsCollector

        if not container.is_registered(GetRequestStatusRESTHandler):
            container.register_singleton(
                GetRequestStatusRESTHandler,
                lambda c: GetRequestStatusRESTHandler(
                    query_bus=c.get(QueryBus),
                    command_bus=c.get(CommandBus),
                    scheduler_strategy=c.get(SchedulerPort),
                    logger=c.get(LoggingPort),
                    error_handler=(
                        c.get(ErrorHandlingPort) if c.is_registered(ErrorHandlingPort) else None
                    ),
                    metrics=(
                        c.get(MetricsCollector) if c.is_registered(MetricsCollector) else None
                    ),
                ),
            )
    except ImportError:
        logger.debug("Request status handler not available for registration")

    try:
        from api.handlers.get_return_requests_handler import GetReturnRequestsRESTHandler
        from domain.base.ports import SchedulerPort, ErrorHandlingPort
        from domain.base.ports.logging_port import LoggingPort
        from infrastructure.di.buses import CommandBus, QueryBus
        from monitoring.metrics import MetricsCollector

        if not container.is_registered(GetReturnRequestsRESTHandler):
            container.register_singleton(
                GetReturnRequestsRESTHandler,
                lambda c: GetReturnRequestsRESTHandler(
                    query_bus=c.get(QueryBus),
                    command_bus=c.get(CommandBus),
                    scheduler_strategy=c.get(SchedulerPort),
                    logger=c.get(LoggingPort),
                    error_handler=(
                        c.get(ErrorHandlingPort) if c.is_registered(ErrorHandlingPort) else None
                    ),
                    metrics=(
                        c.get(MetricsCollector) if c.is_registered(MetricsCollector) else None
                    ),
                ),
            )
    except ImportError:
        logger.debug("Return requests handler not available for registration")

    try:
        from api.handlers.request_return_machines_handler import RequestReturnMachinesRESTHandler
        from domain.base.ports import SchedulerPort, ErrorHandlingPort
        from domain.base.ports.logging_port import LoggingPort
        from infrastructure.di.buses import CommandBus, QueryBus
        from monitoring.metrics import MetricsCollector

        if not container.is_registered(RequestReturnMachinesRESTHandler):
            container.register_singleton(
                RequestReturnMachinesRESTHandler,
                lambda c: RequestReturnMachinesRESTHandler(
                    query_bus=c.get(QueryBus),
                    command_bus=c.get(CommandBus),
                    scheduler_strategy=c.get(SchedulerPort),
                    logger=c.get(LoggingPort),
                    error_handler=(
                        c.get(ErrorHandlingPort) if c.is_registered(ErrorHandlingPort) else None
                    ),
                    metrics=(
                        c.get(MetricsCollector) if c.is_registered(MetricsCollector) else None
                    ),
                ),
            )
    except ImportError:
        logger.debug("Return machines handler not available for registration")
