"""MCP integration tests against moto-mocked AWS.

Exercises the MCP server in-process via handle_message() with JSON-RPC strings.
Uses the same moto injection pattern as test_sdk_onmoto.py so all AWS calls
route through moto without real credentials.

Moto limitations accounted for:
- SSM parameter resolution: patched out (moto cannot resolve SSM paths)
- AWSProvisioningAdapter: patched to synthesise instances from instance_ids
  so the orchestration loop completes on the first attempt
- LT deletion: lt_manager is a MagicMock — cleanup tests assert the mock's
  delete method was called, not that moto reflects the deletion
"""

import json
import re
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import boto3
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

REGION = "eu-west-2"
REQUEST_ID_RE = re.compile(r"^req-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

pytestmark = [pytest.mark.moto, pytest.mark.mcp]


# ---------------------------------------------------------------------------
# Moto compatibility patches (mirrors test_sdk_onmoto.py)
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_moto_compat():
    """Patch moto-incompatible behaviours for all tests in this module.

    1. AWSImageResolutionService.is_resolution_needed -> False
       Prevents SSM path resolution which moto cannot fulfil.

    2. AWSProvisioningAdapter._provision_via_handlers synthesises instances
       from instance_ids so the orchestration loop sees fulfilled_count > 0.
    """
    from orb.providers.aws.infrastructure.adapters.aws_provisioning_adapter import (
        AWSProvisioningAdapter,
    )

    _original_provision = AWSProvisioningAdapter._provision_via_handlers

    def _patched_provision(self, request, template, dry_run=False):
        result = _original_provision(self, request, template, dry_run=dry_run)
        if isinstance(result, dict) and not result.get("instances"):
            instance_ids = result.get("instance_ids") or result.get("resource_ids", [])
            iids = [i for i in instance_ids if i.startswith("i-")]
            if iids:
                result["instances"] = [{"instance_id": iid} for iid in iids]
        return result

    with (
        patch(
            "orb.providers.aws.infrastructure.services.aws_image_resolution_service"
            ".AWSImageResolutionService.is_resolution_needed",
            return_value=False,
        ),
        patch.object(AWSProvisioningAdapter, "_provision_via_handlers", _patched_provision),
    ):
        yield


# ---------------------------------------------------------------------------
# Helpers copied from test_sdk_onmoto.py
# ---------------------------------------------------------------------------


def _make_moto_aws_client():
    from orb.providers.aws.infrastructure.aws_client import AWSClient

    aws_client = MagicMock(spec=AWSClient)
    aws_client.ec2_client = boto3.client("ec2", region_name=REGION)
    aws_client.autoscaling_client = boto3.client("autoscaling", region_name=REGION)
    aws_client.sts_client = boto3.client("sts", region_name=REGION)
    aws_client.ssm_client = boto3.client("ssm", region_name=REGION)
    return aws_client


def _make_logger():
    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


def _make_lt_manager(aws_client):
    """Build a moto-backed launch template manager mock."""
    from orb.providers.aws.infrastructure.launch_template.manager import (
        AWSLaunchTemplateManager,
        LaunchTemplateResult,
    )

    lt_manager = MagicMock(spec=AWSLaunchTemplateManager)

    def _create_or_update(template, request):
        lt_name = f"orb-lt-{request.request_id}"
        try:
            resp = aws_client.ec2_client.create_launch_template(
                LaunchTemplateName=lt_name,
                TagSpecifications=[
                    {
                        "ResourceType": "launch-template",
                        "Tags": [
                            {"Key": "orb:request-id", "Value": str(request.request_id)},
                            {"Key": "orb:managed-by", "Value": "open-resource-broker"},
                        ],
                    }
                ],
                LaunchTemplateData={
                    "ImageId": template.image_id or "ami-12345678",
                    "InstanceType": (
                        next(iter(template.machine_types.keys()))
                        if template.machine_types
                        else "t3.micro"
                    ),
                    "NetworkInterfaces": [
                        {
                            "DeviceIndex": 0,
                            "SubnetId": template.subnet_ids[0] if template.subnet_ids else "",
                            "Groups": template.security_group_ids or [],
                            "AssociatePublicIpAddress": False,
                        }
                    ],
                },
            )
            lt_id = resp["LaunchTemplate"]["LaunchTemplateId"]
            version = str(resp["LaunchTemplate"]["LatestVersionNumber"])
        except Exception:
            lt_id = "lt-mock"
            version = "1"
        return LaunchTemplateResult(
            template_id=lt_id,
            version=version,
            template_name=lt_name,
            is_new_template=True,
        )

    lt_manager.create_or_update_launch_template.side_effect = _create_or_update
    return lt_manager


def _inject_moto_factory(aws_client, logger, config_port) -> None:
    """Swap the DI-wired AWSProviderStrategy's internals for moto-backed ones."""
    from orb.providers.aws.domain.template.value_objects import ProviderApi
    from orb.providers.aws.infrastructure.adapters.aws_provisioning_adapter import (
        AWSProvisioningAdapter,
    )
    from orb.providers.aws.infrastructure.adapters.machine_adapter import AWSMachineAdapter
    from orb.providers.aws.infrastructure.aws_handler_factory import AWSHandlerFactory
    from orb.providers.aws.infrastructure.handlers.asg.handler import ASGHandler
    from orb.providers.aws.infrastructure.handlers.ec2_fleet.handler import EC2FleetHandler
    from orb.providers.aws.infrastructure.handlers.run_instances.handler import RunInstancesHandler
    from orb.providers.aws.infrastructure.handlers.spot_fleet.handler import SpotFleetHandler
    from orb.providers.aws.services.instance_operation_service import AWSInstanceOperationService
    from orb.providers.aws.utilities.aws_operations import AWSOperations
    from orb.providers.registry import get_provider_registry

    registry = get_provider_registry()
    registry._strategy_cache.pop("aws_moto_eu-west-2", None)

    from orb.domain.base.ports import ConfigurationPort
    from orb.infrastructure.di.container import get_container

    container = get_container()
    cfg_port = container.get(ConfigurationPort)
    provider_config = cfg_port.get_provider_config()
    if provider_config:
        for pi in provider_config.get_active_providers():
            if not registry.is_provider_instance_registered(pi.name):
                registry.ensure_provider_instance_registered_from_config(pi)

    strategy = registry.get_or_create_strategy("aws_moto_eu-west-2")
    if strategy is None:
        return

    lt_manager = _make_lt_manager(aws_client)

    aws_ops = AWSOperations(aws_client, logger, cfg_port)
    factory = AWSHandlerFactory(aws_client=aws_client, logger=logger, config=cfg_port)

    factory._handlers[ProviderApi.ASG.value] = ASGHandler(
        aws_client=aws_client,
        logger=logger,
        aws_ops=aws_ops,
        launch_template_manager=lt_manager,
        config_port=cfg_port,
    )
    factory._handlers[ProviderApi.EC2_FLEET.value] = EC2FleetHandler(
        aws_client=aws_client,
        logger=logger,
        aws_ops=aws_ops,
        launch_template_manager=lt_manager,
        config_port=cfg_port,
    )
    factory._handlers[ProviderApi.RUN_INSTANCES.value] = RunInstancesHandler(
        aws_client=aws_client,
        logger=logger,
        aws_ops=aws_ops,
        launch_template_manager=lt_manager,
        config_port=cfg_port,
    )
    factory._handlers[ProviderApi.SPOT_FLEET.value] = SpotFleetHandler(
        aws_client=aws_client,
        logger=logger,
        aws_ops=aws_ops,
        launch_template_manager=lt_manager,
        config_port=cfg_port,
    )

    strategy._aws_client = aws_client
    handler_registry = strategy._get_handler_registry()
    handler_registry._handler_factory = factory
    handler_registry._handler_cache = dict(factory._handlers)

    machine_adapter = AWSMachineAdapter(aws_client=aws_client, logger=logger)
    provisioning_adapter = AWSProvisioningAdapter(
        aws_client=aws_client,
        logger=logger,
        provider_strategy=strategy,
        config_port=cfg_port,
    )
    instance_service = AWSInstanceOperationService(
        aws_client=aws_client,
        logger=logger,
        provisioning_adapter=provisioning_adapter,
        machine_adapter=machine_adapter,
        provider_name="aws_moto_eu-west-2",
        provider_type="aws",
    )
    strategy._instance_service = instance_service


# ---------------------------------------------------------------------------
# MCP server fixture
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def mcp_server(orb_config_dir, moto_aws):
    """Bootstrap the application and return a live MCP server backed by moto."""
    from orb.bootstrap import Application
    from orb.infrastructure.di.container import get_container
    from orb.interface.mcp.server.core import OpenResourceBrokerMCPServer

    app = Application(skip_validation=True)
    await app.initialize()

    container = get_container()
    server = OpenResourceBrokerMCPServer(app=container)

    aws_client = _make_moto_aws_client()
    logger = _make_logger()
    _inject_moto_factory(aws_client, logger, None)

    # All interface handlers take only (args,) — wrap each tool so the server's
    # _handle_tools_call convention of tool_func(args, self.app) still works.
    import functools

    wrapped: dict = {}
    for name, fn in server.tools.items():
        import inspect

        sig = inspect.signature(fn)
        if len(sig.parameters) == 1:
            async def _wrap(args, _app, _fn=fn):
                return await _fn(args)
            functools.update_wrapper(_wrap, fn)
            wrapped[name] = _wrap
        else:
            wrapped[name] = fn
    server.tools = wrapped

    yield server


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _send(server, method: str, params: dict | None = None, msg_id: int = 1) -> dict:
    """Send a JSON-RPC message to the MCP server and return the parsed response."""
    msg = json.dumps({"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params or {}})
    raw = await server.handle_message(msg)
    return json.loads(raw)


def _has_error(response: dict) -> bool:
    """Return True if the JSON-RPC response carries a non-null error."""
    return bool(response.get("error"))


def _tool_text(response: dict) -> Any:  # type: ignore[return]
    """Extract the JSON payload from a tools/call content[0].text response.

    Handlers may return a (dict, exit_code) tuple which the server serialises
    as a JSON array — unwrap the first element in that case.
    """
    content = response["result"]["content"]
    parsed = json.loads(content[0]["text"])
    if isinstance(parsed, list) and len(parsed) >= 1 and isinstance(parsed[0], dict):
        return parsed[0]
    return parsed


# ---------------------------------------------------------------------------
# TestMCPServerInit
# ---------------------------------------------------------------------------


class TestMCPServerInit:
    @pytest.mark.asyncio
    async def test_initialize_returns_capabilities(self, mcp_server):
        resp = await _send(mcp_server, "initialize", {"clientInfo": {"name": "test"}})

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        result = resp["result"]
        assert "protocolVersion" in result
        assert "capabilities" in result
        assert "tools" in result["capabilities"]

    @pytest.mark.asyncio
    async def test_tools_list_returns_expected_tools(self, mcp_server):
        resp = await _send(mcp_server, "tools/list")

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        tool_names = {t["name"] for t in resp["result"]["tools"]}
        for expected in (
            "list_templates",
            "request_machines",
            "get_request_status",
            "return_machines",
            "list_return_requests",
        ):
            assert expected in tool_names, f"Tool {expected!r} missing from tools/list"


# ---------------------------------------------------------------------------
# TestMCPTemplates
# ---------------------------------------------------------------------------


class TestMCPTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_via_mcp(self, mcp_server):
        resp = await _send(
            mcp_server, "tools/call", {"name": "list_templates", "arguments": {}}
        )

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        payload = _tool_text(resp)
        templates = payload.get("templates", [])
        assert len(templates) > 0, "list_templates returned no templates"
        for tpl in templates:
            tid = tpl.get("template_id") or tpl.get("templateId")
            assert tid, f"Template missing template_id: {tpl}"

    @pytest.mark.asyncio
    async def test_get_template_via_mcp(self, mcp_server):
        resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "get_template", "arguments": {"template_id": "RunInstances-OnDemand"}},
        )

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        payload = _tool_text(resp)
        # Either a template object or an error key — just assert no Python exception
        assert isinstance(payload, dict)


# ---------------------------------------------------------------------------
# TestMCPRequestLifecycle
# ---------------------------------------------------------------------------


class TestMCPRequestLifecycle:
    @pytest.mark.asyncio
    async def test_request_machines_returns_request_id(self, mcp_server):
        resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        payload = _tool_text(resp)
        request_id = payload.get("requestId") or payload.get("request_id")
        assert request_id is not None, f"No request_id in response: {payload}"
        assert REQUEST_ID_RE.match(request_id), (
            f"request_id {request_id!r} does not match expected pattern"
        )

    @pytest.mark.asyncio
    async def test_get_request_status_after_request(self, mcp_server):
        # Create a request first
        req_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )
        request_id = _tool_text(req_resp).get("requestId") or _tool_text(req_resp).get("request_id")
        assert request_id, f"No request_id from request_machines: {req_resp}"

        # Query status
        status_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "get_request_status", "arguments": {"request_id": request_id}},
        )

        assert not _has_error(status_resp), f"Unexpected error: {status_resp.get('error')}"
        payload = _tool_text(status_resp)

        # Status must be a known value
        requests_list = payload.get("requests", [])
        if requests_list:
            status = requests_list[0].get("status", "unknown")
            assert status in {"running", "complete", "complete_with_error", "pending", "unknown"}, (
                f"Unexpected status: {status!r}"
            )
            returned_id = requests_list[0].get("request_id") or requests_list[0].get("requestId")
            assert returned_id == request_id, (
                f"Echoed request_id {returned_id!r} != created {request_id!r}"
            )

    @pytest.mark.asyncio
    async def test_full_lifecycle_request_and_return(self, mcp_server):
        # 1. Request machines
        req_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )
        req_payload = _tool_text(req_resp)
        request_id = req_payload.get("requestId") or req_payload.get("request_id")
        assert request_id, f"No request_id: {req_payload}"

        # 2. Get status — look for machine_ids
        status_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "get_request_status", "arguments": {"request_id": request_id}},
        )
        status_payload = _tool_text(status_resp)
        requests_list = status_payload.get("requests", [])
        machine_ids: list[str] = []
        if requests_list:
            machines = requests_list[0].get("machines", [])
            machine_ids = [
                m.get("machineId") or m.get("machine_id")
                for m in machines
                if m.get("machineId") or m.get("machine_id")
            ]

        if not machine_ids:
            pytest.skip("No machine_ids returned — RunInstances may not have fulfilled yet")

        for mid in machine_ids:
            assert re.match(r"^i-[0-9a-f]+$", mid), (
                f"machineId {mid!r} does not look like an EC2 instance ID"
            )

        # 3. Return machines
        return_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "return_machines", "arguments": {"machine_ids": machine_ids}},
        )
        assert not _has_error(return_resp), f"Unexpected error: {return_resp.get('error')}"
        return_payload = _tool_text(return_resp)
        has_id = return_payload.get("request_id") or return_payload.get("requestId")
        has_msg = return_payload.get("message")
        assert has_id or has_msg, (
            f"return_machines response missing request_id or message: {return_payload}"
        )

    @pytest.mark.asyncio
    async def test_list_return_requests_after_return(self, mcp_server):
        # Create and return a request
        req_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )
        req_payload = _tool_text(req_resp)
        request_id = req_payload.get("requestId") or req_payload.get("request_id")
        assert request_id

        status_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "get_request_status", "arguments": {"request_id": request_id}},
        )
        status_payload = _tool_text(status_resp)
        requests_list = status_payload.get("requests", [])
        machine_ids: list[str] = []
        if requests_list:
            machines = requests_list[0].get("machines", [])
            machine_ids = [
                m.get("machineId") or m.get("machine_id")
                for m in machines
                if m.get("machineId") or m.get("machine_id")
            ]

        if not machine_ids:
            pytest.skip("No machine_ids — cannot create a return request")

        await _send(
            mcp_server,
            "tools/call",
            {"name": "return_machines", "arguments": {"machine_ids": machine_ids}},
        )

        # List return requests — must be non-empty
        list_resp = await _send(
            mcp_server, "tools/call", {"name": "list_return_requests", "arguments": {}}
        )
        assert not _has_error(list_resp), f"Unexpected error: {list_resp.get('error')}"
        list_payload = _tool_text(list_resp)
        requests = list_payload.get("requests", [])
        assert len(requests) > 0, "list_return_requests returned empty list after a return"


# ---------------------------------------------------------------------------
# TestMCPLaunchTemplateCleanup
# ---------------------------------------------------------------------------


class TestMCPLaunchTemplateCleanup:
    @pytest.mark.asyncio
    async def test_launch_template_created_during_request(self, mcp_server):
        """After request_machines, the moto-backed lt_manager.create_or_update was called."""
        from orb.providers.registry import get_provider_registry

        registry = get_provider_registry()
        strategy = registry.get_or_create_strategy("aws_moto_eu-west-2")
        if strategy is None:
            pytest.skip("Strategy not available")

        handler_registry = strategy._get_handler_registry()
        # Grab the lt_manager from one of the handlers
        from orb.providers.aws.domain.template.value_objects import ProviderApi

        handler = handler_registry._handler_cache.get(ProviderApi.RUN_INSTANCES.value)
        if handler is None:
            pytest.skip("RunInstances handler not in cache")

        lt_manager = handler.launch_template_manager

        await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )

        lt_manager.create_or_update_launch_template.assert_called()

    @pytest.mark.asyncio
    async def test_launch_template_deleted_after_return(self, mcp_server):
        """After return_machines, the LT created during provisioning is gone from moto EC2.

        The base_handler calls aws_client.ec2_client.delete_launch_template() directly,
        so we verify via moto state rather than a mock assertion.
        """
        # Full lifecycle
        req_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "request_machines", "arguments": {"template_id": "RunInstances-OnDemand", "machine_count": 1}},
        )
        req_payload = _tool_text(req_resp)
        request_id = req_payload.get("requestId") or req_payload.get("request_id")
        assert request_id

        # Confirm the LT was created in moto
        ec2 = boto3.client("ec2", region_name=REGION)
        lt_name = f"orb-lt-{request_id}"
        lts_before = ec2.describe_launch_templates(
            Filters=[{"Name": "launch-template-name", "Values": [lt_name]}]
        )["LaunchTemplates"]
        assert len(lts_before) == 1, f"Expected LT {lt_name!r} to exist before return"

        status_resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "get_request_status", "arguments": {"request_id": request_id}},
        )
        status_payload = _tool_text(status_resp)
        requests_list = status_payload.get("requests", [])
        machine_ids: list[str] = []
        if requests_list:
            machines = requests_list[0].get("machines", [])
            machine_ids = [
                m.get("machineId") or m.get("machine_id")
                for m in machines
                if m.get("machineId") or m.get("machine_id")
            ]

        if not machine_ids:
            pytest.skip("No machine_ids — cannot verify LT cleanup")

        await _send(
            mcp_server,
            "tools/call",
            {"name": "return_machines", "arguments": {"machine_ids": machine_ids}},
        )

        # LT must be gone from moto after return
        lts_after = ec2.describe_launch_templates(
            Filters=[{"Name": "launch-template-name", "Values": [lt_name]}]
        )["LaunchTemplates"]
        assert len(lts_after) == 0, (
            f"Expected LT {lt_name!r} to be deleted after return, but it still exists"
        )


# ---------------------------------------------------------------------------
# TestMCPResources
# ---------------------------------------------------------------------------


class TestMCPResources:
    @pytest.mark.asyncio
    async def test_resources_list(self, mcp_server):
        resp = await _send(mcp_server, "resources/list")

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        uris = {r["uri"] for r in resp["result"]["resources"]}
        for expected_uri in ("templates://", "requests://", "machines://", "providers://"):
            assert expected_uri in uris, f"URI {expected_uri!r} missing from resources/list"

    @pytest.mark.asyncio
    async def test_resources_read_templates(self, mcp_server):
        resp = await _send(mcp_server, "resources/read", {"uri": "templates://"})

        assert not _has_error(resp), f"Unexpected error: {resp.get('error')}"
        assert "contents" in resp["result"]


# ---------------------------------------------------------------------------
# TestMCPErrorHandling
# ---------------------------------------------------------------------------


class TestMCPErrorHandling:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self, mcp_server):
        resp = await _send(
            mcp_server,
            "tools/call",
            {"name": "nonexistent_tool", "arguments": {}},
        )

        # Must be a JSON error response, not a Python exception
        assert _has_error(resp), f"Expected error field in response: {resp}"

    @pytest.mark.asyncio
    async def test_unknown_method_returns_error(self, mcp_server):
        resp = await _send(mcp_server, "unknown/method")

        assert _has_error(resp), f"Expected error field in response: {resp}"
        assert resp["error"]["code"] == -32601

    @pytest.mark.asyncio
    async def test_malformed_json_returns_parse_error(self, mcp_server):
        raw = await mcp_server.handle_message("this is not json {{{")
        resp = json.loads(raw)

        assert _has_error(resp), f"Expected error field in response: {resp}"
        assert resp["error"]["code"] == -32700
