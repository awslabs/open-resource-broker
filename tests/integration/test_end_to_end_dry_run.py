"""End-to-end integration tests for dry-run functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from domain.request.aggregate import Request
from domain.request.value_objects import RequestId, RequestType
from domain.template.template_aggregate import Template
from infrastructure.mocking.dry_run_context import dry_run_context
from providers.aws.configuration.config import AWSProviderConfig
from providers.aws.infrastructure.adapters import AWSProvisioningAdapter
from providers.aws.strategy.aws_provider_strategy import AWSProviderStrategy


class TestEndToEndDryRun:
    """Test end-to-end dry-run functionality from command to provider strategy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = Mock()
        self.aws_config = AWSProviderConfig(region="us-east-1", profile="default")
        self.aws_strategy = AWSProviderStrategy(config=self.aws_config, logger=self.mock_logger)
        self.aws_strategy._initialized = True

        self.mock_aws_client = Mock()
        self.provisioning_adapter = AWSProvisioningAdapter(
            aws_client=self.mock_aws_client,
            logger=self.mock_logger,
            provider_strategy=self.aws_strategy,
        )

    def _make_request(self, dry_run: bool = False) -> Request:
        return Request(
            request_id=RequestId.generate(RequestType.ACQUIRE),
            request_type=RequestType.ACQUIRE,
            provider_type="aws",
            template_id="test-template",
            requested_count=1,
            metadata={"dry_run": dry_run},
        )

    def _make_template(self) -> Template:
        return Template(
            template_id="test-template",
            provider_api="EC2Fleet",
            machine_types={"t2.micro": 1},
            max_number=10,
        )

    def test_dry_run_uses_provider_strategy(self):
        """Dry-run requests are routed through the provider strategy path."""
        request = self._make_request(dry_run=True)
        template = self._make_template()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data = {"instance_ids": ["i-dry-run-001"]}

        mock_execute = AsyncMock(return_value=mock_result)
        self.aws_strategy.execute_operation = mock_execute

        result = asyncio.run(self.provisioning_adapter.provision_resources(request, template))

        assert result == "i-dry-run-001"
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert call_args.context.get("dry_run") is True

    def test_normal_request_uses_handler_path(self):
        """Normal (non-dry-run) requests are routed through the handler path."""
        request = self._make_request(dry_run=False)
        template = self._make_template()

        mock_handler = Mock()
        mock_handler.acquire_hosts.return_value = {
            "success": True,
            "resource_ids": ["fleet-123"],
            "instances": [],
        }

        with patch.object(
            self.provisioning_adapter, "_get_handler_for_template", return_value=mock_handler
        ):
            result = asyncio.run(self.provisioning_adapter.provision_resources(request, template))

        assert result == {"success": True, "resource_ids": ["fleet-123"], "instances": []}
        mock_handler.acquire_hosts.assert_called_once()

    def test_dry_run_strategy_failure_raises(self):
        """A failed strategy operation raises InfrastructureError."""
        from providers.aws.exceptions.aws_exceptions import InfrastructureError

        request = self._make_request(dry_run=True)
        template = self._make_template()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "simulated failure"

        self.aws_strategy.execute_operation = AsyncMock(return_value=mock_result)
        with patch.object(
            self.aws_strategy, "execute_operation", new=AsyncMock(return_value=mock_result)
        ):
            try:
                asyncio.run(self.provisioning_adapter.provision_resources(request, template))
                assert False, "Expected InfrastructureError"
            except InfrastructureError:
                pass

    def test_dry_run_context_manager(self):
        """dry_run_context sets and clears the global dry-run flag."""
        with dry_run_context(True):
            from infrastructure.mocking.dry_run_context import is_dry_run_active

            assert is_dry_run_active()

        from infrastructure.mocking.dry_run_context import is_dry_run_active

        assert not is_dry_run_active()

    def test_no_strategy_falls_back_to_handlers(self):
        """When no provider strategy is set, dry-run falls back to handler path."""
        adapter = AWSProvisioningAdapter(
            aws_client=self.mock_aws_client,
            logger=self.mock_logger,
            provider_strategy=None,
        )
        request = self._make_request(dry_run=True)
        template = self._make_template()

        mock_handler = Mock()
        mock_handler.acquire_hosts.return_value = {
            "success": True,
            "resource_ids": ["fleet-fallback"],
            "instances": [],
        }

        with patch.object(adapter, "_get_handler_for_template", return_value=mock_handler):
            result = asyncio.run(adapter.provision_resources(request, template))

        assert result == {"success": True, "resource_ids": ["fleet-fallback"], "instances": []}
        mock_handler.acquire_hosts.assert_called_once()
