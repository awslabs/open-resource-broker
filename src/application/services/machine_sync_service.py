"""Machine sync service for provider integration."""

from typing import Optional, Tuple

from domain.base.ports.logging_port import LoggingPort
from domain.base.ports.container_port import ContainerPort
from domain.request.aggregate import Request
from domain.machine.aggregate import Machine
from infrastructure.di.buses import CommandBus


class MachineSyncService:
    """Provider synchronization service."""

    def __init__(
        self,
        command_bus: CommandBus,
        container: ContainerPort,
        logger: LoggingPort,
    ) -> None:
        self.command_bus = command_bus
        self.container = container
        self.logger = logger

    async def populate_missing_machine_ids(self, request: Request) -> None:
        """Populate missing machine IDs via command."""
        if request.needs_machine_id_population():
            try:
                from application.dto.commands import PopulateMachineIdsCommand
                populate_command = PopulateMachineIdsCommand(request_id=str(request.request_id.value))
                await self.command_bus.execute(populate_command)
                self.logger.debug(f"Triggered machine ID population for request {request.request_id.value}")
            except Exception as e:
                self.logger.error(f"Failed to populate machine IDs: {e}")

    async def fetch_provider_machines(
        self, 
        request: Request, 
        db_machines: list[Machine]
    ) -> Tuple[list[Machine], dict]:
        """Fetch machines from provider."""
        try:
            # Get provider-specific machine fetching logic
            from providers.registry import get_provider_registry
            
            registry = get_provider_registry()
            provider_strategy = registry.get_strategy(request.provider_name)
            
            if not provider_strategy:
                self.logger.warning(f"No provider strategy found for {request.provider_name}")
                return [], {}
            
            # Use provider strategy to get current machine status
            # This is a simplified version - the actual implementation would be more complex
            return db_machines, {}  # For now, return DB machines as-is
            
        except Exception as e:
            self.logger.error(f"Failed to fetch provider machines: {e}")
            return [], {}

    async def sync_machines_with_provider(
        self, 
        request: Request, 
        db_machines: list[Machine], 
        provider_machines: list[Machine]
    ) -> Tuple[list[Machine], dict]:
        """Sync machine status with cloud provider."""
        try:
            # This would contain the complex AWS sync logic from the original handler
            # For now, return the provider machines as-is
            return provider_machines if provider_machines else db_machines, {}
            
        except Exception as e:
            self.logger.error(f"Failed to sync machines with provider: {e}")
            return db_machines, {}
