"""Tests for EC2FleetConfigurationService."""

import pytest
from unittest.mock import Mock

from domain.request.aggregate import Request
from domain.request.value_objects import RequestId
from providers.aws.domain.template.aws_template_aggregate import AWSTemplate
from providers.aws.domain.template.value_objects import AWSFleetType
from providers.aws.services.ec2_fleet_configuration_service import EC2FleetConfigurationService


class TestEC2FleetConfigurationService:
    """Test cases for EC2FleetConfigurationService."""

    @pytest.fixture
    def logger(self):
        """Mock logger fixture."""
        return Mock()

    @pytest.fixture
    def service(self, logger):
        """EC2FleetConfigurationService fixture."""
        return EC2FleetConfigurationService(logger)

    @pytest.fixture
    def sample_template(self):
        """Sample AWS template fixture."""
        template = Mock(spec=AWSTemplate)
        template.price_type = "spot"
        template.fleet_type = AWSFleetType.REQUEST
        template.machine_types = {"t3.medium": 1, "t3.large": 2}
        template.subnet_ids = ["subnet-123", "subnet-456"]
        template.allocation_strategy = "diversified"
        template.allocation_strategy_on_demand = "lowest-price"
        template.max_price = 0.05
        return template

    @pytest.fixture
    def sample_request(self):
        """Sample request fixture."""
        request = Mock(spec=Request)
        request.request_id = RequestId(value="req-12345678-1234-1234-1234-123456789abc")
        request.requested_count = 5
        return request

    def test_get_default_capacity_type_spot(self, service):
        """Test default capacity type for spot pricing."""
        result = service.get_default_capacity_type("spot")
        assert result == "spot"

    def test_get_default_capacity_type_ondemand(self, service):
        """Test default capacity type for on-demand pricing."""
        result = service.get_default_capacity_type("ondemand")
        assert result == "on-demand"

    def test_get_default_capacity_type_heterogeneous(self, service):
        """Test default capacity type for heterogeneous pricing."""
        result = service.get_default_capacity_type("heterogeneous")
        assert result == "on-demand"

    def test_get_default_capacity_type_none(self, service):
        """Test default capacity type for None pricing."""
        result = service.get_default_capacity_type(None)
        assert result == "on-demand"

    def test_prepare_ec2fleet_specific_context_basic(
        self, service, sample_template, sample_request
    ):
        """Test EC2Fleet-specific context preparation."""
        context = service.prepare_ec2fleet_specific_context(sample_template, sample_request)

        # Check fleet-specific values
        assert context["fleet_type"] == AWSFleetType.REQUEST.value
        assert context["fleet_name"] == f"-{sample_request.request_id.value}"

        # Check instance overrides
        assert len(context["instance_overrides"]) == 4  # 2 subnets × 2 instance types
        assert context["needs_overrides"] is True

        # Check flags
        assert context["is_maintain_fleet"] is False
        assert context["replace_unhealthy"] is False
        assert context["has_spot_options"] is True
        assert context["has_ondemand_options"] is True

        # Check configuration values
        assert context["allocation_strategy"] == "diversified"
        assert context["allocation_strategy_on_demand"] == "lowestPrice"
        assert context["max_spot_price"] == "0.05"
        assert context["default_capacity_type"] == "spot"

    def test_prepare_ec2fleet_specific_context_maintain_fleet(
        self, service, sample_template, sample_request
    ):
        """Test context preparation for maintain fleet type."""
        sample_template.fleet_type = AWSFleetType.MAINTAIN

        context = service.prepare_ec2fleet_specific_context(sample_template, sample_request)

        assert context["is_maintain_fleet"] is True
        assert context["replace_unhealthy"] is True

    def test_prepare_ec2fleet_specific_context_no_subnets(
        self, service, sample_template, sample_request
    ):
        """Test context preparation without subnet IDs."""
        sample_template.subnet_ids = None

        context = service.prepare_ec2fleet_specific_context(sample_template, sample_request)

        # Should have overrides without subnet_id
        assert len(context["instance_overrides"]) == 2  # 2 instance types only
        for override in context["instance_overrides"]:
            assert "subnet_id" not in override

    def test_prepare_ec2fleet_specific_context_heterogeneous(
        self, service, sample_template, sample_request
    ):
        """Test context preparation for heterogeneous pricing."""
        sample_template.price_type = "heterogeneous"
        sample_template.machine_types_ondemand = {"m5.large": 1, "m5.xlarge": 2}

        context = service.prepare_ec2fleet_specific_context(sample_template, sample_request)

        # Check on-demand overrides
        assert len(context["ondemand_overrides"]) == 2
        assert context["ondemand_overrides"][0]["instance_type"] == "m5.large"
        assert context["ondemand_overrides"][1]["instance_type"] == "m5.xlarge"

    def test_prepare_template_context(self, service, sample_template, sample_request):
        """Test complete template context preparation."""
        base_context = {"base_key": "base_value"}

        context = service.prepare_template_context(sample_template, sample_request, base_context)

        # Should include base context
        assert context["base_key"] == "base_value"

        # Should include EC2Fleet-specific context
        assert "fleet_type" in context
        assert "fleet_name" in context
        assert "instance_overrides" in context

    def test_allocation_strategy_mapping(self, service):
        """Test allocation strategy mapping."""
        assert service._get_allocation_strategy("lowest-price") == "lowestPrice"
        assert service._get_allocation_strategy("diversified") == "diversified"
        assert service._get_allocation_strategy("capacity-optimized") == "capacityOptimized"
        assert (
            service._get_allocation_strategy("capacity-optimized-prioritized")
            == "capacityOptimizedPrioritized"
        )
        assert service._get_allocation_strategy("unknown") == "lowestPrice"

    def test_allocation_strategy_on_demand_mapping(self, service):
        """Test on-demand allocation strategy mapping."""
        assert service._get_allocation_strategy_on_demand("lowest-price") == "lowestPrice"
        assert service._get_allocation_strategy_on_demand("other") == "prioritized"
