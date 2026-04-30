"""Unit tests for RequestDTOFactory.map_machine_status_to_result."""

import json

import pytest

from orb.application.factories.request_dto_factory import RequestDTOFactory
from orb.domain.base.value_objects import InstanceType, Tags
from orb.domain.machine.aggregate import Machine
from orb.domain.machine.machine_identifiers import MachineId
from orb.domain.machine.machine_status import MachineStatus
from orb.domain.request.aggregate import Request
from orb.domain.request.request_types import RequestType


@pytest.fixture
def factory():
    return RequestDTOFactory()


class TestMapMachineStatusToResultReturnRequest:
    def test_shutting_down_is_executing(self, factory):
        assert (
            factory.map_machine_status_to_result("shutting-down", RequestType.RETURN) == "executing"
        )

    def test_stopping_is_executing(self, factory):
        assert factory.map_machine_status_to_result("stopping", RequestType.RETURN) == "executing"

    def test_terminated_is_succeed(self, factory):
        assert factory.map_machine_status_to_result("terminated", RequestType.RETURN) == "succeed"

    def test_stopped_is_succeed(self, factory):
        assert factory.map_machine_status_to_result("stopped", RequestType.RETURN) == "succeed"

    def test_failed_is_fail(self, factory):
        assert factory.map_machine_status_to_result("failed", RequestType.RETURN) == "fail"

    def test_pending_is_executing(self, factory):
        assert factory.map_machine_status_to_result("pending", RequestType.RETURN) == "executing"


def _make_machine(**overrides) -> Machine:
    defaults = dict(
        machine_id=MachineId(value="i-1234567890abcdef0"),
        template_id="template-001",
        request_id="request-001",
        provider_type="aws",
        provider_name="aws-us-east-1",
        instance_type=InstanceType(value="m5.large"),
        image_id="ami-12345678",
        status=MachineStatus.RUNNING,
        price_type="ondemand",
        tags=Tags(tags={"Environment": "prod", "Owner": "team-x"}),
    )
    defaults.update(overrides)
    return Machine(**defaults)


def _make_request() -> Request:
    return Request.create_new_request(
        request_type=RequestType.ACQUIRE,
        template_id="template-001",
        machine_count=1,
        provider_type="aws",
    )


class TestCreateFromDomainForwardsHFFields:
    """Regression: instance_type, price_type, tags must flow Machine → DTO."""

    def test_populated_fields_forwarded(self, factory):
        machine = _make_machine()
        dto = factory.create_from_domain(_make_request(), [machine])

        assert len(dto.machine_references) == 1
        ref = dto.machine_references[0]
        assert ref.instance_type == "m5.large"
        assert ref.price_type == "ondemand"
        # Tags serialized as JSON string with sorted keys for determinism.
        assert ref.instance_tags == json.dumps(
            {"Environment": "prod", "Owner": "team-x"}, sort_keys=True
        )

    def test_empty_tags_serialize_to_none(self, factory):
        machine = _make_machine(tags=Tags(tags={}))
        dto = factory.create_from_domain(_make_request(), [machine])

        assert dto.machine_references[0].instance_tags is None

    def test_missing_price_type_forwarded_as_none(self, factory):
        machine = _make_machine(price_type=None)
        dto = factory.create_from_domain(_make_request(), [machine])

        assert dto.machine_references[0].price_type is None
