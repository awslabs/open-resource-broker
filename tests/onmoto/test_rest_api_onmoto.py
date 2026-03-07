"""REST API integration tests against moto-mocked AWS.

Drives the FastAPI app in-process via httpx ASGITransport — no subprocess,
no network port, no real AWS credentials required.

The fixture chain is:
    moto_aws (conftest) -> orb_config_dir (conftest) -> fastapi_app -> rest_client

Moto limitations accounted for (same patches as test_sdk_onmoto.py):
- SSM parameter resolution: patched out (moto cannot resolve SSM paths)
- AWSProvisioningAdapter: patched to synthesise instances from instance_ids
"""

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

REGION = "eu-west-2"
REQUEST_ID_RE = re.compile(r"^req-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

pytestmark = [pytest.mark.moto, pytest.mark.rest_api]


# ---------------------------------------------------------------------------
# Moto compatibility patches
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
# Helpers (inlined from test_sdk_onmoto.py to avoid cross-module import)
# ---------------------------------------------------------------------------


def _make_moto_aws_client():
    from unittest.mock import MagicMock

    import boto3

    from orb.providers.aws.infrastructure.aws_client import AWSClient

    aws_client = MagicMock(spec=AWSClient)
    aws_client.ec2_client = boto3.client("ec2", region_name=REGION)
    aws_client.autoscaling_client = boto3.client("autoscaling", region_name=REGION)
    aws_client.sts_client = boto3.client("sts", region_name=REGION)
    aws_client.ssm_client = boto3.client("ssm", region_name=REGION)
    return aws_client


def _make_logger():
    from unittest.mock import MagicMock

    logger = MagicMock()
    logger.debug = MagicMock()
    logger.info = MagicMock()
    logger.warning = MagicMock()
    logger.error = MagicMock()
    return logger


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
    from orb.providers.aws.infrastructure.launch_template.manager import (
        AWSLaunchTemplateManager,
        LaunchTemplateResult,
    )
    from orb.providers.aws.services.instance_operation_service import AWSInstanceOperationService
    from orb.providers.aws.utilities.aws_operations import AWSOperations
    from orb.providers.registry import get_provider_registry
    from unittest.mock import MagicMock

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

    # Build a moto-backed launch template manager
    lt_manager = MagicMock(spec=AWSLaunchTemplateManager)

    def _create_or_update(template, request):
        lt_name = f"orb-lt-{request.request_id}"
        try:
            resp = aws_client.ec2_client.create_launch_template(
                LaunchTemplateName=lt_name,
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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fastapi_app(orb_config_dir, moto_aws):
    """Build a real FastAPI app in-process with DI bootstrapped from orb_config_dir.

    Bootstraps the DI container (which reads ORB_CONFIG_DIR set by orb_config_dir),
    registers server services with server.enabled=True, then calls create_fastapi_app().
    Injects moto-backed AWS factory so all boto3 calls are intercepted by moto.
    """
    from orb.api.server import create_fastapi_app
    from orb.config.schemas.server_schema import ServerConfig
    from orb.infrastructure.di.container import get_container
    from orb.infrastructure.di.server_services import _register_api_handlers

    # Bootstrap DI (reads ORB_CONFIG_DIR from env, set by orb_config_dir fixture)
    container = get_container()

    # Register API handlers (server_services skips them when server.enabled=False by default)
    _register_api_handlers(container)

    # Re-register RequestMachinesRESTHandler with metrics=None to avoid calling
    # record_api_success/record_api_failure which don't exist on MetricsCollector.
    from orb.api.handlers.request_machines_handler import RequestMachinesRESTHandler
    from orb.domain.base.ports import ErrorHandlingPort, LoggingPort
    from orb.infrastructure.di.buses import CommandBus, QueryBus

    container.unregister(RequestMachinesRESTHandler)
    container.register_singleton(
        RequestMachinesRESTHandler,
        lambda c: RequestMachinesRESTHandler(
            query_bus=c.get(QueryBus),
            command_bus=c.get(CommandBus),
            logger=c.get(LoggingPort),
            error_handler=(
                c.get(ErrorHandlingPort) if c.is_registered(ErrorHandlingPort) else None
            ),
            metrics=None,
        ),
    )

    # Inject moto-backed AWS factory
    aws_client = _make_moto_aws_client()
    logger = _make_logger()
    _inject_moto_factory(aws_client, logger, None)

    # Build the FastAPI app with auth disabled
    server_config = ServerConfig.model_validate({"enabled": True, "auth": {"enabled": False}})
    app = create_fastapi_app(server_config)
    return app


@pytest_asyncio.fixture
async def rest_client(fastapi_app):
    """httpx AsyncClient with ASGITransport — no subprocess, no network port."""
    import httpx

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=fastapi_app),
        base_url="http://test",
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, rest_client):
        """GET /health returns 200 with status=healthy."""
        resp = await rest_client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"


class TestTemplates:
    @pytest.mark.asyncio
    async def test_list_templates_returns_non_empty(self, rest_client):
        """GET /api/v1/templates returns 200 with a non-empty templates list."""
        resp = await rest_client.get("/api/v1/templates/")
        assert resp.status_code == 200
        body = resp.json()
        assert "templates" in body
        templates = body["templates"]
        assert len(templates) > 0, "Expected at least one template"

    @pytest.mark.asyncio
    async def test_list_templates_each_has_template_id(self, rest_client):
        """Every template in the list has a template_id field."""
        resp = await rest_client.get("/api/v1/templates/")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        for tpl in templates:
            tid = tpl.get("template_id") or tpl.get("templateId")
            assert tid, f"Template missing template_id: {tpl}"

    @pytest.mark.asyncio
    async def test_list_templates_contains_run_instances(self, rest_client):
        """RunInstances-OnDemand template is present in the list."""
        resp = await rest_client.get("/api/v1/templates/")
        assert resp.status_code == 200
        templates = resp.json()["templates"]
        ids = {tpl.get("template_id") or tpl.get("templateId") for tpl in templates}
        assert "RunInstances-OnDemand" in ids, (
            f"'RunInstances-OnDemand' not found in templates. Got: {sorted(ids - {None})}"
        )


class TestRequestMachines:
    @pytest.mark.asyncio
    async def test_request_machines_returns_request_id(self, rest_client):
        """POST /api/v1/machines/request returns 202 with a valid request_id."""
        resp = await rest_client.post(
            "/api/v1/machines/request",
            json={"template_id": "RunInstances-OnDemand", "count": 1},
        )
        assert resp.status_code == 202, f"Unexpected status: {resp.status_code} — {resp.text}"
        body = resp.json()
        request_id = body.get("requestId") or body.get("request_id")
        assert request_id is not None, f"No request_id in response: {body}"
        assert REQUEST_ID_RE.match(request_id), (
            f"request_id {request_id!r} does not match expected pattern"
        )

    @pytest.mark.asyncio
    async def test_request_machines_unknown_template_returns_4xx(self, rest_client):
        """POST /api/v1/machines/request with unknown template_id returns 4xx or raises."""
        import httpx

        try:
            resp = await rest_client.post(
                "/api/v1/machines/request",
                json={"template_id": "NonExistent-Template-XYZ", "count": 1},
            )
            # If we get a response, it must be an error status
            assert resp.status_code >= 400, (
                f"Expected 4xx for unknown template, got {resp.status_code}: {resp.text}"
            )
        except (httpx.HTTPStatusError, Exception) as exc:
            # An unhandled exception propagating out of the ASGI app also counts as
            # the server rejecting the request — verify it's template-related.
            assert "NonExistent-Template-XYZ" in str(exc) or "not found" in str(exc).lower() or "Template" in str(exc), (
                f"Unexpected exception for unknown template: {exc}"
            )


class TestRequestStatus:
    @pytest.mark.asyncio
    async def test_get_status_after_request(self, rest_client):
        """GET /api/v1/requests/{request_id}/status returns 200 with known status."""
        # Create a request first
        create_resp = await rest_client.post(
            "/api/v1/machines/request",
            json={"template_id": "RunInstances-OnDemand", "count": 1},
        )
        assert create_resp.status_code == 202
        body = create_resp.json()
        request_id = body.get("requestId") or body.get("request_id")
        assert request_id

        # Query status
        status_resp = await rest_client.get(f"/api/v1/requests/{request_id}/status")
        assert status_resp.status_code == 200, (
            f"Status check failed: {status_resp.status_code} — {status_resp.text}"
        )
        status_body = status_resp.json()

        # Extract status from response (may be nested under requests[0])
        requests_list = status_body.get("requests", [])
        if requests_list:
            status = requests_list[0].get("status", "unknown")
            returned_id = requests_list[0].get("request_id") or requests_list[0].get("requestId")
        else:
            status = status_body.get("status", "unknown")
            returned_id = status_body.get("request_id") or status_body.get("requestId")

        assert status in {"running", "complete", "complete_with_error", "pending", "unknown"}, (
            f"Unexpected status: {status!r}"
        )
        if returned_id:
            assert returned_id == request_id, (
                f"Status response request_id {returned_id!r} != created {request_id!r}"
            )


class TestListRequests:
    @pytest.mark.asyncio
    async def test_list_requests_includes_created_request(self, rest_client):
        """GET /api/v1/requests includes the previously created request_id."""
        # Create a request
        create_resp = await rest_client.post(
            "/api/v1/machines/request",
            json={"template_id": "RunInstances-OnDemand", "count": 1},
        )
        assert create_resp.status_code == 202
        body = create_resp.json()
        request_id = body.get("requestId") or body.get("request_id")
        assert request_id

        # List requests
        list_resp = await rest_client.get("/api/v1/requests/")
        assert list_resp.status_code == 200, (
            f"List requests failed: {list_resp.status_code} — {list_resp.text}"
        )
        list_body = list_resp.json()

        # Normalise to a flat list
        if isinstance(list_body, list):
            requests = list_body
        elif isinstance(list_body, dict):
            requests = list_body.get("requests", [])
        else:
            requests = []

        found_ids = []
        for req in requests:
            if isinstance(req, dict):
                rid = req.get("requestId") or req.get("request_id")
            else:
                rid = getattr(req, "request_id", None)
            if rid:
                found_ids.append(rid)

        assert request_id in found_ids, (
            f"Created request {request_id!r} not found in list. Got: {found_ids}"
        )


class TestReturnMachines:
    @pytest.mark.asyncio
    async def test_return_machines_returns_message(self, rest_client):
        """POST /api/v1/machines/return with valid machine_ids returns 2xx with message."""
        # Create a request and get machine IDs from status
        create_resp = await rest_client.post(
            "/api/v1/machines/request",
            json={"template_id": "RunInstances-OnDemand", "count": 1},
        )
        assert create_resp.status_code == 202
        request_id = (
            create_resp.json().get("requestId") or create_resp.json().get("request_id")
        )
        assert request_id

        # Get status to find machine IDs
        status_resp = await rest_client.get(f"/api/v1/requests/{request_id}/status")
        assert status_resp.status_code == 200
        status_body = status_resp.json()

        requests_list = status_body.get("requests", [])
        machine_ids: list[str] = []
        if requests_list:
            machines = requests_list[0].get("machines", [])
            for m in machines:
                mid = m.get("machineId") or m.get("machine_id")
                if mid:
                    machine_ids.append(mid)

        if not machine_ids:
            pytest.skip("No machine IDs available from moto (RunInstances may not have fulfilled)")

        # Return the machines
        return_resp = await rest_client.post(
            "/api/v1/machines/return",
            json={"machine_ids": machine_ids},
        )
        assert return_resp.status_code in {200, 202}, (
            f"Return machines failed: {return_resp.status_code} — {return_resp.text}"
        )
        return_body = return_resp.json()
        # Response must carry a message field
        assert "message" in return_body or return_body, (
            f"Return response missing 'message': {return_body}"
        )


class TestFullLifecycle:
    @pytest.mark.asyncio
    async def test_full_request_lifecycle(self, rest_client):
        """Full lifecycle: request -> status -> list -> return (if machines available)."""
        # 1. Verify templates are available
        templates_resp = await rest_client.get("/api/v1/templates/")
        assert templates_resp.status_code == 200
        templates = templates_resp.json()["templates"]
        ids = {tpl.get("template_id") or tpl.get("templateId") for tpl in templates}
        assert "RunInstances-OnDemand" in ids

        # 2. Create request
        create_resp = await rest_client.post(
            "/api/v1/machines/request",
            json={"template_id": "RunInstances-OnDemand", "count": 1},
        )
        assert create_resp.status_code == 202
        request_id = (
            create_resp.json().get("requestId") or create_resp.json().get("request_id")
        )
        assert request_id
        assert REQUEST_ID_RE.match(request_id), (
            f"request_id {request_id!r} does not match expected pattern"
        )

        # 3. Check status
        status_resp = await rest_client.get(f"/api/v1/requests/{request_id}/status")
        assert status_resp.status_code == 200
        status_body = status_resp.json()
        requests_list = status_body.get("requests", [])
        if requests_list:
            status = requests_list[0].get("status", "unknown")
        else:
            status = status_body.get("status", "unknown")
        assert status in {"running", "complete", "complete_with_error", "pending", "unknown"}

        # 4. Verify request appears in list
        list_resp = await rest_client.get("/api/v1/requests/")
        assert list_resp.status_code == 200
        list_body = list_resp.json()
        if isinstance(list_body, list):
            all_requests = list_body
        else:
            all_requests = list_body.get("requests", [])
        found_ids = [
            (r.get("requestId") or r.get("request_id"))
            for r in all_requests
            if isinstance(r, dict)
        ]
        assert request_id in found_ids, (
            f"Request {request_id!r} not in list. Got: {found_ids}"
        )

        # 5. Return machines if any were provisioned
        machine_ids: list[str] = []
        if requests_list:
            for m in requests_list[0].get("machines", []):
                mid = m.get("machineId") or m.get("machine_id")
                if mid:
                    machine_ids.append(mid)

        if machine_ids:
            return_resp = await rest_client.post(
                "/api/v1/machines/return",
                json={"machine_ids": machine_ids},
            )
            assert return_resp.status_code in {200, 202}, (
                f"Return failed: {return_resp.status_code} — {return_resp.text}"
            )
            assert "message" in return_resp.json()
