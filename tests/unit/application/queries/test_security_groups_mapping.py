"""Test SecurityGroups mapping in query handlers."""

from unittest.mock import Mock

from application.queries.handlers import GetRequestHandler
from domain.request.request_identifiers import RequestId


class TestSecurityGroupsMapping:
    """Test SecurityGroups mapping from AWS format to security_group_ids."""

    def test_create_machine_from_aws_data_extracts_security_group_ids(self):
        """Test that SecurityGroups dicts are mapped to security_group_ids list."""
        # Arrange - Create handler with mocked dependencies
        handler = GetRequestHandler(
            uow_factory=Mock(),
            logger=Mock(),
            error_handler=Mock(),
            container=Mock(),
            command_bus=Mock(),
            provider_registry_service=Mock(),
        )

        # Mock request
        request = Mock()
        request.request_id = RequestId(value="req-12345678-1234-1234-1234-123456789abc")
        request.template_id = "template-1"
        request.provider_type = "aws"
        request.provider_name = "aws-test"
        request.provider_api = "EC2Fleet"
        request.metadata = {"provider_api": "EC2Fleet"}
        request.resource_ids = ["fleet-123"]

        # AWS instance data with SecurityGroups as list of dicts (actual AWS format)
        aws_instance = {
            "InstanceId": "i-1234567890abcdef0",
            "State": {"Name": "running"},
            "InstanceType": "t3.micro",
            "ImageId": "ami-12345678",
            "PrivateIpAddress": "10.0.1.100",
            "PublicIpAddress": "54.123.45.67",
            "LaunchTime": "2024-01-01T12:00:00Z",
            "SubnetId": "subnet-12345",
            "SecurityGroups": [
                {"GroupId": "sg-123", "GroupName": "default"},
                {"GroupId": "sg-456", "GroupName": "web-servers"},
            ],
            "Tags": [{"Key": "Name", "Value": "test-instance"}],
        }

        # Act
        machine = handler._create_machine_from_aws_data(aws_instance, request)

        # Assert
        assert machine.security_group_ids == ["sg-123", "sg-456"]
        assert isinstance(machine.security_group_ids, list)
        assert all(isinstance(sg_id, str) for sg_id in machine.security_group_ids)

    def test_create_machine_from_aws_data_handles_empty_security_groups(self):
        """Test that empty SecurityGroups list is handled correctly."""
        # Arrange
        handler = GetRequestHandler(
            uow_factory=Mock(),
            logger=Mock(),
            error_handler=Mock(),
            container=Mock(),
            command_bus=Mock(),
            provider_registry_service=Mock(),
        )

        # Mock request
        request = Mock()
        request.request_id = RequestId(value="req-12345678-1234-1234-1234-123456789abc")
        request.template_id = "template-1"
        request.provider_type = "aws"
        request.provider_name = "aws-test"
        request.provider_api = "EC2Fleet"
        request.metadata = {"provider_api": "EC2Fleet"}
        request.resource_ids = ["fleet-123"]

        # AWS instance data with empty SecurityGroups
        aws_instance = {
            "InstanceId": "i-1234567890abcdef0",
            "State": {"Name": "running"},
            "InstanceType": "t3.micro",
            "ImageId": "ami-12345678",
            "SecurityGroups": [],
            "Tags": [],
        }

        # Act
        machine = handler._create_machine_from_aws_data(aws_instance, request)

        # Assert
        assert machine.security_group_ids == []
        assert isinstance(machine.security_group_ids, list)

    def test_create_machine_from_aws_data_handles_missing_security_groups(self):
        """Test that missing SecurityGroups field is handled correctly."""
        # Arrange
        handler = GetRequestHandler(
            uow_factory=Mock(),
            logger=Mock(),
            error_handler=Mock(),
            container=Mock(),
            command_bus=Mock(),
            provider_registry_service=Mock(),
        )

        # Mock request
        request = Mock()
        request.request_id = RequestId(value="req-12345678-1234-1234-1234-123456789abc")
        request.template_id = "template-1"
        request.provider_type = "aws"
        request.provider_name = "aws-test"
        request.provider_api = "EC2Fleet"
        request.metadata = {"provider_api": "EC2Fleet"}
        request.resource_ids = ["fleet-123"]

        # AWS instance data without SecurityGroups field
        aws_instance = {
            "InstanceId": "i-1234567890abcdef0",
            "State": {"Name": "running"},
            "InstanceType": "t3.micro",
            "ImageId": "ami-12345678",
            "Tags": [],
        }

        # Act
        machine = handler._create_machine_from_aws_data(aws_instance, request)

        # Assert
        assert machine.security_group_ids == []
        assert isinstance(machine.security_group_ids, list)
