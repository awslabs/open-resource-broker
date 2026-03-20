"""Unit tests for AWSMachineAdapter — snake_case input path."""

from unittest.mock import MagicMock

from orb.providers.aws.infrastructure.adapters.machine_adapter import AWSMachineAdapter


def _make_adapter():
    return AWSMachineAdapter(aws_client=MagicMock(), logger=MagicMock())


_SNAKE_BASE = {
    "instance_id": "i-0abc123",
    "instance_type": "t3.medium",
    "private_ip": "10.0.0.1",
    "status": "running",
    "image_id": "ami-0abc123",
    "subnet_id": "subnet-111",
    "vpc_id": "vpc-111",
    "placement": {"availability_zone": "us-east-1a"},
    "security_groups": [],
    "launch_time": "2026-01-01T00:00:00+00:00",
}


def _call(adapter, data, **kwargs):
    return adapter.create_machine_from_aws_instance(
        aws_instance_data=data,
        request_id=kwargs.get("request_id", "req-001"),
        provider_api=kwargs.get("provider_api", "EC2Fleet"),
        resource_id=kwargs.get("resource_id", "fleet-001"),
    )


class TestSnakeCasePrivateDnsName:
    def test_snake_case_key_is_resolved(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "private_dns_name": "ip-10-0-0-1.ec2.internal"}
        result = _call(adapter, data)
        assert result["private_dns_name"] == "ip-10-0-0-1.ec2.internal"

    def test_snake_takes_priority_over_pascal(self):
        adapter = _make_adapter()
        data = {
            **_SNAKE_BASE,
            "private_dns_name": "snake.internal",
            "PrivateDnsName": "pascal.internal",
        }
        result = _call(adapter, data)
        assert result["private_dns_name"] == "snake.internal"

    def test_falls_back_to_pascal_when_snake_absent(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "PrivateDnsName": "pascal.internal"}
        result = _call(adapter, data)
        assert result["private_dns_name"] == "pascal.internal"

    def test_none_when_both_absent(self):
        adapter = _make_adapter()
        result = _call(adapter, dict(_SNAKE_BASE))
        assert result["private_dns_name"] is None


class TestSnakeCasePublicDnsName:
    def test_snake_case_key_is_resolved(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "public_dns_name": "ec2-1-2-3-4.compute-1.amazonaws.com"}
        result = _call(adapter, data)
        assert result["public_dns_name"] == "ec2-1-2-3-4.compute-1.amazonaws.com"

    def test_falls_back_to_pascal_when_snake_absent(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "PublicDnsName": "ec2-pascal.compute-1.amazonaws.com"}
        result = _call(adapter, data)
        assert result["public_dns_name"] == "ec2-pascal.compute-1.amazonaws.com"

    def test_none_when_both_absent(self):
        adapter = _make_adapter()
        result = _call(adapter, dict(_SNAKE_BASE))
        assert result["public_dns_name"] is None


class TestSnakeCaseInstanceId:
    def test_instance_id_preserved(self):
        adapter = _make_adapter()
        result = _call(adapter, dict(_SNAKE_BASE))
        assert result["instance_id"] == "i-0abc123"

    def test_request_id_injected(self):
        adapter = _make_adapter()
        result = _call(adapter, dict(_SNAKE_BASE), request_id="req-xyz")
        assert result["request_id"] == "req-xyz"


class TestSnakeCaseTags:
    def test_name_tag_list_format(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "tags": [{"Key": "Name", "Value": "my-machine"}]}
        result = _call(adapter, data)
        assert result["name"] == "my-machine"

    def test_name_tag_dict_format(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "tags": {"Name": "dict-machine"}}
        result = _call(adapter, data)
        assert result["name"] == "dict-machine"

    def test_pascal_tags_fallback(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "Tags": [{"Key": "Name", "Value": "pascal-machine"}]}
        result = _call(adapter, data)
        assert result["name"] == "pascal-machine"

    def test_no_tags_falls_back_to_private_dns(self):
        adapter = _make_adapter()
        data = {**_SNAKE_BASE, "private_dns_name": "ip-10-0-0-1.ec2.internal"}
        result = _call(adapter, data)
        assert result["name"] == "ip-10-0-0-1.ec2.internal"

    def test_no_tags_no_dns_falls_back_to_instance_id(self):
        adapter = _make_adapter()
        data = {k: v for k, v in _SNAKE_BASE.items() if k != "private_ip"}
        result = _call(adapter, data)
        assert result["name"] == "i-0abc123"


class TestResolveMachineName:
    def test_snake_private_dns(self):
        adapter = _make_adapter()
        data = {"instance_id": "i-001", "private_dns_name": "ip-10.ec2.internal"}
        assert adapter._resolve_machine_name(data) == "ip-10.ec2.internal"

    def test_pascal_private_dns_fallback(self):
        adapter = _make_adapter()
        data = {"instance_id": "i-001", "PrivateDnsName": "ip-10.ec2.internal"}
        assert adapter._resolve_machine_name(data) == "ip-10.ec2.internal"

    def test_snake_instance_id_fallback(self):
        adapter = _make_adapter()
        data = {"instance_id": "i-fallback"}
        assert adapter._resolve_machine_name(data) == "i-fallback"

    def test_pascal_instance_id_fallback(self):
        adapter = _make_adapter()
        data = {"InstanceId": "i-pascal-fallback"}
        assert adapter._resolve_machine_name(data) == "i-pascal-fallback"

    def test_snake_private_ip_fallback(self):
        adapter = _make_adapter()
        data = {"instance_id": "i-001", "private_ip": "10.0.0.5"}
        assert adapter._resolve_machine_name(data) == "10.0.0.5"


class TestCloudHostId:
    def test_snake_case_sets_cloud_host_id(self):
        adapter = _make_adapter()
        result = _call(adapter, dict(_SNAKE_BASE))
        assert result["provider_data"]["cloud_host_id"] == "i-0abc123"

    def test_pascal_case_sets_cloud_host_id(self):
        adapter = _make_adapter()
        data = {
            "InstanceId": "i-pascal",
            "InstanceType": "t3.medium",
            "State": {"Name": "running"},
            "Placement": {"AvailabilityZone": "us-east-1a"},
            "SubnetId": "subnet-111",
            "VpcId": "vpc-111",
            "ImageId": "ami-0abc123",
            "PrivateIpAddress": "10.0.0.1",
            "SecurityGroups": [],
        }
        result = _call(adapter, data)
        assert result["provider_data"]["cloud_host_id"] == "i-pascal"
