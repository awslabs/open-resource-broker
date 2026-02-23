"""Unit tests for RequestStatusManagementService._update_request_status logic."""

import pytest
from unittest.mock import MagicMock, patch

from application.services.request_status_management_service import RequestStatusManagementService
from application.services.provisioning_orchestration_service import ProvisioningResult
from domain.request.request_types import RequestStatus


def _make_service():
    uow_factory = MagicMock()
    logger = MagicMock()
    return RequestStatusManagementService(uow_factory=uow_factory, logger=logger)


def _make_request(requested_count=2):
    req = MagicMock()
    req.request_id = "req-a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    req.requested_count = requested_count
    req.template_id = "tmpl-001"
    req.provider_type = "aws"
    req.provider_name = "aws-prod"
    req.provider_api = "RunInstances"
    req.metadata = {}
    req.provider_data = {}
    req.add_resource_id = MagicMock(return_value=req)
    req.add_machine_ids = MagicMock(return_value=req)
    req.update_status = MagicMock(return_value=req)
    return req


class TestUpdateRequestStatus:
    def setup_method(self):
        self.svc = _make_service()

    def test_full_success_sets_completed(self):
        req = _make_request(requested_count=2)
        result = self.svc._update_request_status(
            request=req,
            instance_count=2,
            requested_count=2,
            has_api_errors=False,
            provider_errors=[],
        )
        req.update_status.assert_called_once()
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.COMPLETED

    def test_full_count_with_errors_sets_partial(self):
        req = _make_request(requested_count=2)
        errors = [{"error_code": "InsufficientCapacity", "error_message": "No capacity"}]
        result = self.svc._update_request_status(
            request=req,
            instance_count=2,
            requested_count=2,
            has_api_errors=True,
            provider_errors=errors,
        )
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.PARTIAL

    def test_partial_count_no_errors_sets_partial(self):
        req = _make_request(requested_count=5)
        result = self.svc._update_request_status(
            request=req,
            instance_count=3,
            requested_count=5,
            has_api_errors=False,
            provider_errors=[],
        )
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.PARTIAL

    def test_partial_count_with_errors_sets_partial(self):
        req = _make_request(requested_count=5)
        errors = [{"error_code": "Throttling", "error_message": "Rate exceeded"}]
        result = self.svc._update_request_status(
            request=req,
            instance_count=2,
            requested_count=5,
            has_api_errors=True,
            provider_errors=errors,
        )
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.PARTIAL

    def test_zero_instances_sets_in_progress(self):
        req = _make_request(requested_count=3)
        result = self.svc._update_request_status(
            request=req,
            instance_count=0,
            requested_count=3,
            has_api_errors=False,
            provider_errors=[],
        )
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.IN_PROGRESS

    def test_error_summary_included_in_message(self):
        req = _make_request(requested_count=2)
        errors = [{"error_code": "InsufficientCapacity", "error_message": "No capacity"}]
        self.svc._update_request_status(
            request=req,
            instance_count=2,
            requested_count=2,
            has_api_errors=True,
            provider_errors=errors,
        )
        call_args = req.update_status.call_args[0]
        assert "InsufficientCapacity" in call_args[1]


class TestHandleProvisioningFailure:
    def setup_method(self):
        self.svc = _make_service()

    def test_sets_failed_status(self):
        req = _make_request()
        prov_result = MagicMock()
        prov_result.error_message = "Provider timeout"
        result = self.svc._handle_provisioning_failure(req, prov_result)
        req.update_status.assert_called_once()
        call_args = req.update_status.call_args[0]
        assert call_args[0] == RequestStatus.FAILED

    def test_stores_error_in_metadata(self):
        req = _make_request()
        prov_result = MagicMock()
        prov_result.error_message = "Provider timeout"
        self.svc._handle_provisioning_failure(req, prov_result)
        assert req.metadata["error_message"] == "Provider timeout"
        assert req.metadata["error_type"] == "ProvisioningFailure"

    def test_unknown_error_message_fallback(self):
        req = _make_request()
        prov_result = MagicMock()
        prov_result.error_message = None
        self.svc._handle_provisioning_failure(req, prov_result)
        assert req.metadata["error_message"] == "Unknown error"


class TestExtractInstanceIds:
    def setup_method(self):
        self.svc = _make_service()

    def test_extract_from_instance_ids_key(self):
        # _extract_instance_ids uses dict-style access: result.get() and result["key"]
        result = {"instance_ids": ["i-abc", "i-def"]}
        ids = self.svc._extract_instance_ids(result)
        assert ids == ["i-abc", "i-def"]

    def test_extract_from_instances_list(self):
        result = {
            "instances": [
                {"instance_id": "i-aaa"},
                {"instance_id": "i-bbb"},
            ]
        }
        ids = self.svc._extract_instance_ids(result)
        assert ids == ["i-aaa", "i-bbb"]

    def test_extract_skips_instances_without_id(self):
        result = {
            "instances": [
                {"instance_id": "i-aaa"},
                {"other_key": "no-id"},
            ]
        }
        ids = self.svc._extract_instance_ids(result)
        assert ids == ["i-aaa"]

    def test_returns_empty_when_no_relevant_keys(self):
        result = {"other": "data"}
        ids = self.svc._extract_instance_ids(result)
        assert ids == []

    def test_returns_empty_on_attribute_error(self):
        # Pass an object that raises AttributeError on .get()
        class BadResult:
            def get(self, *a):
                raise AttributeError("no get")
        ids = self.svc._extract_instance_ids(BadResult())
        assert ids == []


class TestCreateMachineAggregate:
    def setup_method(self):
        self.svc = _make_service()

    def test_creates_machine_with_basic_data(self):
        req = _make_request()
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t3.medium",
            "image_id": "ami-12345678",
        }
        machine = self.svc._create_machine_aggregate(instance_data, req, "tmpl-001")
        assert str(machine.machine_id) == "i-1234567890abcdef0"
        assert str(machine.instance_type) == "t3.medium"

    def test_creates_machine_with_string_launch_time(self):
        req = _make_request()
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t3.medium",
            "image_id": "ami-12345678",
            "launch_time": "2026-01-01T00:00:00",
        }
        machine = self.svc._create_machine_aggregate(instance_data, req, "tmpl-001")
        assert machine.launch_time is not None

    def test_creates_machine_with_invalid_launch_time(self):
        req = _make_request()
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "instance_type": "t3.medium",
            "image_id": "ami-12345678",
            "launch_time": "not-a-date",
        }
        machine = self.svc._create_machine_aggregate(instance_data, req, "tmpl-001")
        assert machine.launch_time is None

    def test_default_instance_type_fallback(self):
        req = _make_request()
        instance_data = {
            "instance_id": "i-1234567890abcdef0",
            "image_id": "ami-12345678",
        }
        machine = self.svc._create_machine_aggregate(instance_data, req, "tmpl-001")
        assert str(machine.instance_type) == "t2.micro"
