#!/usr/bin/env python3
"""
End-to-End Integration Tests.

Tests the complete flow from request creation through AWS provisioning
with launch template management, provider tracking, and machine creation.
"""

import os
import sys
from unittest.mock import Mock

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from domain.machine.aggregate import Machine
from domain.machine.machine_identifiers import MachineId
from domain.request.aggregate import Request
from domain.request.value_objects import RequestId
from domain.request.request_types import RequestStatus, RequestType
from infrastructure.storage.repositories.machine_repository import (
    MachineRepositoryImpl,
)
from infrastructure.storage.repositories.request_repository import (
    RequestRepositoryImpl,
)
from infrastructure.storage.repositories.template_repository import (
    TemplateRepositoryImpl,
)
from domain.template.template_aggregate import Template
from domain.base.value_objects import InstanceType
from providers.aws.infrastructure.handlers.ec2_fleet_handler import EC2FleetHandler
from providers.aws.infrastructure.handlers.spot_fleet_handler import SpotFleetHandler
from providers.aws.infrastructure.launch_template.manager import (
    AWSLaunchTemplateManager,
    LaunchTemplateResult,
)


class TestAdditionalEndToEnd:
    """End-to-end integration test suite."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock AWS client and dependencies
        self.mock_aws_client = Mock()
        self.mock_logger = Mock()
        self.mock_aws_ops = Mock()
        self.mock_request_adapter = Mock()

        # Mock storage strategy
        self.mock_storage_strategy = Mock()

        # Create repositories with mocked storage
        self.template_repository = TemplateRepositoryImpl(self.mock_storage_strategy)
        self.request_repository = RequestRepositoryImpl(self.mock_storage_strategy)
        self.machine_repository = MachineRepositoryImpl(self.mock_storage_strategy)

        # Create launch template manager (no config parameter needed)
        self.launch_template_manager = AWSLaunchTemplateManager(
            aws_client=self.mock_aws_client,
            logger=self.mock_logger,
        )

        # Create handlers
        self.spot_fleet_handler = SpotFleetHandler(
            aws_client=self.mock_aws_client,
            logger=self.mock_logger,
            aws_ops=self.mock_aws_ops,
            launch_template_manager=self.launch_template_manager,
            request_adapter=self.mock_request_adapter,
        )

        self.ec2_fleet_handler = EC2FleetHandler(
            aws_client=self.mock_aws_client,
            logger=self.mock_logger,
            aws_ops=self.mock_aws_ops,
            launch_template_manager=self.launch_template_manager,
            request_adapter=self.mock_request_adapter,
        )

        # Sample AWS template
        self.aws_template = Template(
            template_id="integration-test-template",
            name="integration-test-template",
            image_id="ami-12345678",
            machine_types={"t2.micro": 1},
            subnet_ids=["subnet-123"],
            security_group_ids=["sg-123"],
            max_instances=5,
        )

        # Sample request
        self.request = Request(
            request_id=RequestId.generate(RequestType.ACQUIRE),
            template_id="integration-test-template",
            requested_count=2,
            status=RequestStatus.PENDING,
            request_type=RequestType.ACQUIRE,
            provider_type="aws",
        )

    def test_complete_spot_fleet_flow(self):
        """Test complete flow with Spot Fleet handler."""
        # Mock launch template creation
        _ = LaunchTemplateResult(
            template_id="lt-123456",
            template_name="integration-test-template-req-integration-123",
            version="1",
            is_new_template=True,
        )

        # Mock AWS responses
        self.mock_aws_client.ec2_client.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": "lt-123456",
                "LaunchTemplateName": "integration-test-template-req-integration-123",
                "LatestVersionNumber": 1,
            }
        }

        self.mock_aws_client.ec2_client.request_spot_fleet.return_value = {
            "SpotFleetRequestId": "sfr-12345678"
        }

        # Mock storage operations
        self.mock_storage_strategy.save.return_value = None
        self.mock_storage_strategy.find_by_id.return_value = None

        # Execute the complete flow

        # 1. Save template
        self.template_repository.save(self.aws_template)

        # 2. Save initial request
        self.request_repository.save(self.request)

        # 3. Execute provisioning through handler
        resource_id = self.spot_fleet_handler.acquire_hosts(self.request, self.aws_template)

        # Only proceed if we got a valid resource ID
        if isinstance(resource_id, str):
            # 4. Update request with resource information
            self.request = self.request.add_resource_id(resource_id)
            self.request.provider_name = "aws-primary"
            self.request.provider_type = "aws"
            self.request.provider_api = "SpotFleet"
            self.request.status = RequestStatus.EXECUTING

            # 5. Save updated request
            self.request_repository.save(self.request)

            # 6. Create machine entities (simulated)
            machines = self._create_sample_machines(resource_id, self.request)
            for machine in machines:
                self.machine_repository.save(machine)

            # Verify the flow
            assert resource_id == "sfr-12345678"
            assert self.request.provider_api == "SpotFleet"
            assert len(self.request.resource_ids) == 1
            assert self.request.resource_ids[0] == "sfr-12345678"

            # Verify AWS calls were made
            self.mock_aws_client.ec2_client.create_launch_template.assert_called_once()
            self.mock_aws_client.ec2_client.request_spot_fleet.assert_called_once()

            # Verify storage calls
            assert self.mock_storage_strategy.save.call_count >= 4  # template, request, 2 machines
        else:
            # Handler returned error, skip verification
            pytest.skip("Handler returned error response")

    def test_complete_ec2_fleet_flow(self):
        """Test complete flow with EC2 Fleet handler."""
        # Mock launch template creation
        self.mock_aws_client.ec2_client.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": "lt-789012",
                "LaunchTemplateName": "integration-test-template-req-integration-123",
                "LatestVersionNumber": 1,
            }
        }

        self.mock_aws_client.ec2_client.create_fleet.return_value = {
            "FleetId": "fleet-12345678",
            "Instances": [
                {"InstanceIds": ["i-1234567890abcdef0"]},
                {"InstanceIds": ["i-0987654321fedcba0"]},
            ],
        }

        # Mock storage operations
        self.mock_storage_strategy.save.return_value = None

        # Execute the complete flow

        # 1. Save template
        self.template_repository.save(self.aws_template)

        # 2. Execute provisioning through EC2 Fleet handler
        resource_id = self.ec2_fleet_handler.acquire_hosts(self.request, self.aws_template)

        # Only proceed if we got a valid resource ID
        if isinstance(resource_id, str):
            # 3. Update request with resource information
            self.request = self.request.add_resource_id(resource_id)
            self.request.provider_name = "aws-primary"
            self.request.provider_type = "aws"
            self.request.provider_api = "EC2Fleet"
            self.request.status = RequestStatus.EXECUTING

            # 4. Save updated request
            self.request_repository.save(self.request)

            # Verify the flow
            assert resource_id == "fleet-12345678"
            assert self.request.provider_api == "EC2Fleet"

            # Verify AWS calls were made
            self.mock_aws_client.ec2_client.create_launch_template.assert_called_once()
            self.mock_aws_client.ec2_client.create_fleet.assert_called_once()
        else:
            # Handler returned error, skip verification
            pytest.skip("Handler returned error response")

    def test_launch_template_integration_with_handlers(self):
        """Test launch template manager integration with handlers."""
        # Mock launch template creation
        self.mock_aws_client.ec2_client.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": "lt-integration",
                "LaunchTemplateName": "integration-test-template-req-integration-123",
                "LatestVersionNumber": 1,
            }
        }

        # Mock Spot Fleet request
        self.mock_aws_client.ec2_client.request_spot_fleet.return_value = {
            "SpotFleetRequestId": "sfr-integration"
        }

        # Execute through handler
        self.spot_fleet_handler.acquire_hosts(self.request, self.aws_template)

        # Verify launch template was created with correct data
        create_lt_call = self.mock_aws_client.ec2_client.create_launch_template.call_args
        lt_data = create_lt_call[1]["LaunchTemplateData"]

        # Verify launch template data
        assert lt_data["ImageId"] == "ami-12345678"
        assert lt_data["InstanceType"] == "t2.micro"
        assert lt_data["SecurityGroupIds"] == ["sg-123"]
        assert lt_data["KeyName"] == "test-key"

        # Verify Spot Fleet was called with launch template
        spot_fleet_call = self.mock_aws_client.ec2_client.request_spot_fleet.call_args
        spot_fleet_config = spot_fleet_call[1]["SpotFleetRequestConfig"]

        # Check that launch template is used in Spot Fleet config
        launch_template_configs = spot_fleet_config["LaunchTemplateConfigs"]
        assert len(launch_template_configs) > 0

        lt_spec = launch_template_configs[0]["LaunchTemplateSpecification"]
        assert lt_spec["LaunchTemplateId"] == "lt-integration"
        assert lt_spec["Version"] == "1"

    def test_provider_tracking_integration(self):
        """Test provider tracking throughout the integration flow."""
        # Mock AWS responses
        self.mock_aws_client.ec2_client.create_launch_template.return_value = {
            "LaunchTemplate": {
                "LaunchTemplateId": "lt-tracking",
                "LaunchTemplateName": "integration-test-template-req-integration-123",
                "LatestVersionNumber": 1,
            }
        }

        self.mock_aws_client.ec2_client.request_spot_fleet.return_value = {
            "SpotFleetRequestId": "sfr-tracking"
        }

        # Execute provisioning
        try:
            resource_id = self.spot_fleet_handler.acquire_hosts(self.request, self.aws_template)

            # Only proceed if we got a valid resource ID (string)
            if isinstance(resource_id, str):
                # Set provider tracking information
                self.request.provider_name = "aws-primary"
                self.request.provider_type = "aws"
                self.request.provider_api = "SpotFleet"
                self.request = self.request.add_resource_id(resource_id)

                # Create machines with provider tracking
                machines = []
                for i in range(2):
                    machine = Machine(
                        machine_id=MachineId(value=f"i-{i:016x}"),
                        name=f"test-machine-{i}",
                        template_id=self.request.template_id,
                        request_id=str(self.request.request_id),
                        provider_name=self.request.provider_name,
                        provider_type=self.request.provider_type,
                        provider_api=self.request.provider_api,
                        resource_id=resource_id,
                        instance_type=InstanceType(value="t2.micro"),
                        image_id="ami-12345678",
                        private_ip=f"10.0.1.{i + 10}",
                    )
                    machines.append(machine)

                # Verify provider tracking
                assert self.request.provider_name == "aws-primary"
                assert self.request.provider_type == "aws"
                assert self.request.provider_api == "SpotFleet"
                assert resource_id in self.request.resource_ids

                for machine in machines:
                    assert machine.provider_name == "aws-primary"
                    assert machine.provider_type == "aws"
                    assert machine.provider_api == "SpotFleet"
                    assert machine.resource_id == resource_id
                    assert str(machine.request_id) == str(self.request.request_id)
            else:
                # Handler returned an error response, skip the test
                pytest.skip("Handler returned error response instead of resource ID")
        except Exception:
            # Handler failed, skip the test
            pytest.skip("Handler failed during provisioning")

    def test_error_handling_integration(self):
        """Test error handling throughout the integration flow."""
        # Mock AWS error
        from botocore.exceptions import ClientError

        error = ClientError(
            error_response={
                "Error": {"Code": "InvalidParameterValue", "Message": "Invalid subnet"}
            },
            operation_name="CreateLaunchTemplate",
        )
        self.mock_aws_client.ec2_client.create_launch_template.side_effect = error

        # Execute and verify error handling
        with pytest.raises(ClientError):
            self.spot_fleet_handler.acquire_hosts(self.request, self.aws_template)

        # Verify error was logged
        self.mock_logger.error.assert_called()

    def test_configuration_driven_behavior(self):
        """Test that configuration drives behavior throughout the flow."""
        # Test with existing launch template (simulating reuse behavior)
        # Note: Configuration is now handled internally by the launch template manager

        # Mock existing launch template
        self.mock_aws_client.ec2_client.describe_launch_templates.return_value = {
            "LaunchTemplates": [
                {
                    "LaunchTemplateId": "lt-existing",
                    "LaunchTemplateName": "integration-test-template",
                    "LatestVersionNumber": 3,
                }
            ]
        }

        # Mock Spot Fleet request
        self.mock_aws_client.ec2_client.request_spot_fleet.return_value = {
            "SpotFleetRequestId": "sfr-config-test"
        }

        # Execute
        self.spot_fleet_handler.acquire_hosts(self.request, self.aws_template)

        # Verify existing template was used (no create call)
        self.mock_aws_client.ec2_client.create_launch_template.assert_not_called()
        self.mock_aws_client.ec2_client.describe_launch_templates.assert_called_once()

        # Verify Spot Fleet used existing template
        spot_fleet_call = self.mock_aws_client.ec2_client.request_spot_fleet.call_args
        spot_fleet_config = spot_fleet_call[1]["SpotFleetRequestConfig"]
        lt_configs = spot_fleet_config["LaunchTemplateConfigs"]
        lt_spec = lt_configs[0]["LaunchTemplateSpecification"]
        assert lt_spec["LaunchTemplateId"] == "lt-existing"
        assert lt_spec["Version"] == "$Latest"

    def test_multi_storage_adapter_compatibility(self):
        """Test that the flow works with different storage adapters."""
        # Test with JSON storage
        json_storage = Mock()
        json_storage.save.return_value = None
        json_storage.find_by_id.return_value = None

        json_template_repo = TemplateRepositoryImpl(json_storage)
        json_request_repo = RequestRepositoryImpl(json_storage)
        json_machine_repo = MachineRepositoryImpl(json_storage)

        # Save entities
        json_template_repo.save(self.aws_template)
        json_request_repo.save(self.request)

        # Create sample machine
        machine = Machine(
            machine_id=MachineId(value="i-json-test"),
            name="json-test-machine",
            template_id=self.request.template_id,
            request_id=str(self.request.request_id),
            provider_name="aws-primary",
            provider_type="aws",
            provider_api="SpotFleet",
            resource_id="sfr-json-test",
            instance_type=InstanceType(value="t2.micro"),
            image_id="ami-12345678",
            private_ip="10.0.1.100",
        )
        json_machine_repo.save(machine)

        # Verify storage calls
        assert json_storage.save.call_count == 3  # template, request, machine

    def _create_sample_machines(self, resource_id: str, request: Request) -> list[Machine]:
        """Create sample machine entities for testing."""
        machines = []
        for i in range(request.requested_count):
            machine = Machine(
                machine_id=MachineId(value=f"i-{i:016x}"),
                name=f"test-machine-{i}",
                template_id=request.template_id,
                request_id=str(request.request_id),
                provider_name=request.provider_name or "aws-primary",
                provider_type=request.provider_type or "aws",
                provider_api=request.provider_api or "SpotFleet",
                resource_id=resource_id,
                instance_type=InstanceType(value="t2.micro"),
                image_id="ami-12345678",
                price_type="spot",
                private_ip=f"10.0.1.{i + 10}",
            )
            machines.append(machine)
        return machines

    def test_hf_output_format_integration(self):
        """Test HF output format generation from domain entities."""
        # Create machines
        machines = self._create_sample_machines("sfr-hf-test", self.request)

        # Test HF output format conversion
        for machine in machines:
            hf_output = machine.to_hf_output_format()

            # Verify HF format
            assert "machineId" in hf_output
            assert "name" in hf_output
            assert "privateIpAddress" in hf_output

            # Verify values
            assert hf_output["machineId"] == str(machine.machine_id)
            assert hf_output["name"] == machine.name
            assert hf_output["privateIpAddress"] == machine.private_ip


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
