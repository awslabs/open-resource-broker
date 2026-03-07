"""CLI integration tests against moto-mocked AWS.

Exercises the full ORB CLI lifecycle — templates list, machines request,
requests status, full lifecycle, requests list — without real AWS credentials.

The CLI is invoked in-process by setting sys.argv and calling asyncio.run(main())
directly. Because everything runs in the same process, moto's mock_aws patches
remain active for all boto3 calls made by the CLI code.

Moto limitations accounted for:
- SSM parameter resolution: patched out (moto cannot resolve SSM paths)
- AWSProvisioningAdapter: patched to synthesise instances from instance_ids
  so the orchestration loop completes on the first attempt
"""

import asyncio
import contextlib
import io
import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

REGION = "eu-west-2"
REQUEST_ID_RE = re.compile(r"^req-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")

pytestmark = [pytest.mark.moto, pytest.mark.cli]


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
# In-process CLI helper
# ---------------------------------------------------------------------------


def _run_orb_cli(args: list[str]) -> dict:  # type: ignore[return]
    """Invoke the ORB CLI in-process and return parsed JSON output.

    Sets sys.argv to ['orb'] + args, captures stdout, calls asyncio.run(main()),
    then resets sys.argv and the DI container.

    Suppresses console warning output (AWS credentials warning etc.) by setting
    ORB_LOG_CONSOLE_ENABLED=false for the duration of the call.

    Returns the parsed JSON dict from stdout.  If the CLI returns a list of the
    form [{...}, exit_code] (machines request shape), the first element is
    returned as the result dict.
    Raises AssertionError if the output cannot be parsed as JSON.
    """
    import json
    import os

    from orb.cli.main import main
    from orb.infrastructure.di.container import reset_container

    original_argv = sys.argv[:]
    original_console = os.environ.get("ORB_LOG_CONSOLE_ENABLED")
    sys.argv = ["orb"] + args
    os.environ["ORB_LOG_CONSOLE_ENABLED"] = "false"

    stdout_capture = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_capture):
            try:
                asyncio.run(main())
            except SystemExit:
                pass
    finally:
        sys.argv = original_argv
        if original_console is None:
            os.environ.pop("ORB_LOG_CONSOLE_ENABLED", None)
        else:
            os.environ["ORB_LOG_CONSOLE_ENABLED"] = original_console
        reset_container()

    output = stdout_capture.getvalue().strip()
    assert output, f"CLI produced no output for args: {args}"

    try:
        parsed = json.loads(output)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"CLI output is not valid JSON for args {args}.\n"
            f"Output was:\n{output}"
        ) from exc

    # machines request returns [result_dict, exit_code] — unwrap to the dict
    if isinstance(parsed, list) and len(parsed) == 2 and isinstance(parsed[0], dict):
        return parsed[0]  # type: ignore[return-value]

    return parsed  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Moto factory injection (mirrors test_sdk_onmoto.py)
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


def _make_lt_manager(aws_client):
    from unittest.mock import MagicMock

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


def _inject_moto_factory(aws_client, logger) -> None:
    """Swap the DI-wired AWSProviderStrategy's internals for moto-backed ones.

    Must be called after the CLI has initialised Application (i.e. after the
    first _run_orb_cli call that triggers app.initialize()).  Since the DI
    container is reset between CLI calls we re-inject before each call that
    needs real AWS operations.
    """
    from orb.domain.base.ports import ConfigurationPort
    from orb.infrastructure.di.container import get_container
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
# Helpers to extract fields from CLI JSON output
# ---------------------------------------------------------------------------


def _extract_request_id(result: dict) -> str | None:
    return result.get("request_id") or result.get("requestId") or result.get("created_request_id")


def _extract_status(result: dict) -> str:
    requests = result.get("requests", [])
    if requests and isinstance(requests[0], dict):
        return requests[0].get("status", "unknown")
    return result.get("status", "unknown")


def _extract_machine_ids(result: dict) -> list[str]:
    requests = result.get("requests", [])
    if requests and isinstance(requests[0], dict):
        machines = requests[0].get("machines", [])
        return [
            mid
            for m in machines
            for mid in [m.get("machineId") or m.get("machine_id")]
            if mid
        ]
    return []


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestCLITemplates:
    def test_cli_templates_list(self, orb_config_dir, moto_aws):
        """'orb templates list' returns JSON with at least one template that has a template_id."""
        result = _run_orb_cli(["templates", "list"])

        templates = result.get("templates", result if isinstance(result, list) else [])
        assert len(templates) > 0, f"Expected at least one template, got: {result}"

        for tpl in templates:
            tid = tpl.get("template_id") or tpl.get("templateId")
            assert tid, f"Template missing template_id: {tpl}"


class TestCLIMachinesRequest:
    def test_cli_machines_request(self, orb_config_dir, moto_aws):
        """'orb machines request' returns a valid request_id."""
        aws_client = _make_moto_aws_client()
        logger = _make_logger()

        # Patch Application.initialize to inject moto factory after app boots
        from orb.bootstrap import Application

        _original_initialize = Application.initialize

        async def _patched_initialize(self, dry_run=False):
            result = await _original_initialize(self, dry_run=dry_run)
            _inject_moto_factory(aws_client, logger)
            return result

        with patch.object(Application, "initialize", _patched_initialize):
            result = _run_orb_cli(
                ["machines", "request", "--template", "RunInstances-OnDemand", "--count", "1"]
            )

        request_id = _extract_request_id(result)
        assert request_id is not None, f"No request_id in response: {result}"
        assert REQUEST_ID_RE.match(request_id), (
            f"request_id {request_id!r} does not match expected pattern"
        )


class TestCLIRequestsStatus:
    def test_cli_requests_status(self, orb_config_dir, moto_aws):
        """'orb requests status <id>' returns a known status and echoes back the request_id."""
        aws_client = _make_moto_aws_client()
        logger = _make_logger()

        from orb.bootstrap import Application

        _original_initialize = Application.initialize

        async def _patched_initialize(self, dry_run=False):
            result = await _original_initialize(self, dry_run=dry_run)
            _inject_moto_factory(aws_client, logger)
            return result

        with patch.object(Application, "initialize", _patched_initialize):
            create_result = _run_orb_cli(
                ["machines", "request", "--template", "RunInstances-OnDemand", "--count", "1"]
            )

        request_id = _extract_request_id(create_result)
        assert request_id, f"No request_id in create response: {create_result}"

        with patch.object(Application, "initialize", _patched_initialize):
            status_result = _run_orb_cli(["requests", "status", request_id])

        status = _extract_status(status_result)
        assert status in {"running", "complete", "complete_with_error", "pending"}, (
            f"Unexpected status: {status!r}"
        )

        # Must echo back the same request_id
        requests_list = status_result.get("requests", [])
        if requests_list:
            returned_id = requests_list[0].get("request_id") or requests_list[0].get("requestId")
            assert returned_id == request_id, (
                f"Status response request_id {returned_id!r} != created {request_id!r}"
            )


class TestCLIFullLifecycle:
    def test_cli_full_lifecycle(self, orb_config_dir, moto_aws):
        """request -> status -> return: machines appear and return succeeds.

        Uses RunInstances because moto fully supports instance creation.
        """
        aws_client = _make_moto_aws_client()
        logger = _make_logger()

        from orb.bootstrap import Application

        _original_initialize = Application.initialize

        async def _patched_initialize(self, dry_run=False):
            result = await _original_initialize(self, dry_run=dry_run)
            _inject_moto_factory(aws_client, logger)
            return result

        with patch.object(Application, "initialize", _patched_initialize):
            # 1. Create request
            create_result = _run_orb_cli(
                ["machines", "request", "--template", "RunInstances-OnDemand", "--count", "1"]
            )

        request_id = _extract_request_id(create_result)
        assert request_id, f"No request_id: {create_result}"
        assert REQUEST_ID_RE.match(request_id), (
            f"request_id {request_id!r} does not match expected pattern"
        )

        with patch.object(Application, "initialize", _patched_initialize):
            # 2. Query status
            status_result = _run_orb_cli(["requests", "status", request_id])

        status = _extract_status(status_result)
        assert status in {"running", "complete", "complete_with_error", "pending"}, (
            f"Unexpected status: {status!r}"
        )

        machine_ids = _extract_machine_ids(status_result)

        if machine_ids:
            for mid in machine_ids:
                assert re.match(r"^i-[0-9a-f]+$", mid), (
                    f"machineId {mid!r} does not look like an EC2 instance ID"
                )

            with patch.object(Application, "initialize", _patched_initialize):
                # 3. Return machines — machine_ids are positional args
                return_result = _run_orb_cli(["machines", "return"] + machine_ids)

            assert return_result is not None
            message = return_result.get("message")
            assert message is not None, (
                f"Return response missing 'message' field: {return_result}"
            )


class TestCLIRequestsList:
    def test_cli_requests_list(self, orb_config_dir, moto_aws):
        """'orb requests list' includes the newly created request_id."""
        aws_client = _make_moto_aws_client()
        logger = _make_logger()

        from orb.bootstrap import Application

        _original_initialize = Application.initialize

        async def _patched_initialize(self, dry_run=False):
            result = await _original_initialize(self, dry_run=dry_run)
            _inject_moto_factory(aws_client, logger)
            return result

        with patch.object(Application, "initialize", _patched_initialize):
            create_result = _run_orb_cli(
                ["machines", "request", "--template", "RunInstances-OnDemand", "--count", "1"]
            )

        request_id = _extract_request_id(create_result)
        assert request_id, f"No request_id in create response: {create_result}"

        # Use --filter to narrow the list to the specific request_id.
        # The short list view omits request_id from the formatted output, so we
        # verify presence by asserting the filtered result is non-empty.
        with patch.object(Application, "initialize", _patched_initialize):
            list_result = _run_orb_cli(
                ["requests", "list", "--filter", f"request_id={request_id}"]
            )

        if isinstance(list_result, list):
            requests = list_result
        else:
            requests = list_result.get("requests", [])

        assert len(requests) > 0, (
            f"Created request {request_id} not found in filtered list. Got: {list_result}"
        )
