"""EC2 Fleet Configuration Service.

This service handles configuration and context preparation for EC2 Fleet operations,
extracted from EC2FleetHandler to follow Single Responsibility Principle.
"""

from typing import Any

from domain.base.dependency_injection import injectable
from domain.base.ports import LoggingPort
from domain.request.aggregate import Request
from infrastructure.utilities.common.resource_naming import get_resource_prefix
from providers.aws.domain.template.aws_template_aggregate import AWSTemplate
from providers.aws.domain.template.value_objects import AWSFleetType


@injectable
class EC2FleetConfigurationService:
    """Service for EC2 Fleet configuration and context preparation."""

    def __init__(self, logger: LoggingPort) -> None:
        """Initialize the configuration service.

        Args:
            logger: Logger for logging messages
        """
        self._logger = logger

    def prepare_template_context(
        self, template: AWSTemplate, request: Request, base_context: dict[str, Any]
    ) -> dict[str, Any]:
        """Prepare context with all computed values for template rendering.

        Args:
            template: AWS template with configuration
            request: Request containing request details
            base_context: Base context from handler

        Returns:
            Complete context dictionary for template rendering
        """
        # Start with base context
        context = base_context.copy()

        # Add EC2Fleet-specific context
        context.update(self.prepare_ec2fleet_specific_context(template, request))

        return context

    def prepare_ec2fleet_specific_context(
        self, template: AWSTemplate, request: Request
    ) -> dict[str, Any]:
        """Prepare EC2Fleet-specific context.

        Args:
            template: AWS template with EC2Fleet configuration
            request: Request containing request details

        Returns:
            Dictionary with EC2Fleet-specific context values
        """
        # Instance overrides computation
        instance_overrides = []
        if template.machine_types and template.subnet_ids:
            for subnet_id in template.subnet_ids:
                for instance_type, weight in template.machine_types.items():
                    instance_overrides.append(
                        {
                            "instance_type": instance_type,
                            "subnet_id": subnet_id,
                            "weighted_capacity": weight,
                        }
                    )
        elif template.machine_types:
            for instance_type, weight in template.machine_types.items():
                instance_overrides.append(
                    {"instance_type": instance_type, "weighted_capacity": weight}
                )

        # On-demand instance overrides for heterogeneous fleets
        ondemand_overrides = []
        if (
            template.price_type == "heterogeneous"
            and hasattr(template, "machine_types_ondemand")
            and template.machine_types_ondemand
        ):
            for instance_type, weight in template.machine_types_ondemand.items():
                ondemand_overrides.append(
                    {"instance_type": instance_type, "weighted_capacity": weight}
                )

        return {
            # Fleet-specific values
            "fleet_type": template.fleet_type.value,
            "fleet_name": f"{get_resource_prefix('fleet')}-{request.request_id}",
            # Computed overrides
            "instance_overrides": instance_overrides,
            "ondemand_overrides": ondemand_overrides,
            "needs_overrides": bool(instance_overrides or ondemand_overrides),
            # Fleet-specific flags
            "is_maintain_fleet": template.fleet_type == AWSFleetType.MAINTAIN.value,
            "replace_unhealthy": template.fleet_type == AWSFleetType.MAINTAIN.value,
            "has_spot_options": bool(template.allocation_strategy or template.max_price),
            "has_ondemand_options": bool(template.allocation_strategy_on_demand),
            # Configuration values
            "allocation_strategy": (
                self._get_allocation_strategy(template.allocation_strategy)
                if template.allocation_strategy
                else None
            ),
            "allocation_strategy_on_demand": (
                self._get_allocation_strategy_on_demand(template.allocation_strategy_on_demand)
                if template.allocation_strategy_on_demand
                else None
            ),
            "max_spot_price": (str(template.max_price) if template.max_price is not None else None),
            "default_capacity_type": self.get_default_capacity_type(template.price_type),
        }

    def get_default_capacity_type(self, price_type: str) -> str:
        """Get default target capacity type based on price type.

        Args:
            price_type: Price type from template (spot, ondemand, heterogeneous)

        Returns:
            Default capacity type for EC2 Fleet
        """
        if price_type == "spot":
            return "spot"
        elif price_type == "ondemand":
            return "on-demand"
        else:  # heterogeneous or None
            return "on-demand"

    def _get_allocation_strategy(self, strategy: str) -> str:
        """Get allocation strategy for spot instances.

        Args:
            strategy: Strategy name from template

        Returns:
            Valid AWS allocation strategy
        """
        strategy_mapping = {
            "lowest-price": "lowestPrice",
            "diversified": "diversified",
            "capacity-optimized": "capacityOptimized",
            "capacity-optimized-prioritized": "capacityOptimizedPrioritized",
        }
        return strategy_mapping.get(strategy, "lowestPrice")

    def _get_allocation_strategy_on_demand(self, strategy: str) -> str:
        """Get allocation strategy for on-demand instances.

        Args:
            strategy: Strategy name from template

        Returns:
            Valid AWS on-demand allocation strategy
        """
        return "lowestPrice" if strategy == "lowest-price" else "prioritized"
