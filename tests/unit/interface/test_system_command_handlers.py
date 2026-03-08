"""Unit tests for system_command_handlers.

Handlers fall into two groups:
- CQRS-compliant: dispatch through QueryBus — tested by asserting the correct query type
  is passed to a mocked bus.
- Non-bus: interact with the container or other infrastructure directly — tested by
  mocking those dependencies.
"""

import argparse
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _ns(**kwargs) -> argparse.Namespace:
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _mock_container_with_query_bus(query_return=None):
    """Return (container, query_bus) with query_bus.execute returning query_return."""
    from orb.infrastructure.di.buses import QueryBus

    container = MagicMock()
    query_bus = AsyncMock()
    query_bus.execute = AsyncMock(return_value=query_return)
    container.get.side_effect = lambda t: query_bus if t is QueryBus else MagicMock()
    return container, query_bus


# ---------------------------------------------------------------------------
# Stub handlers — not implemented, return error='Not implemented'
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStubHandlers:
    @pytest.mark.asyncio
    async def test_handle_validate_provider_config_returns_not_implemented(self):
        from orb.interface.system_command_handlers import handle_validate_provider_config

        result = await handle_validate_provider_config(_ns())

        assert isinstance(result, dict)
        assert result.get("error") == "Not implemented"

    @pytest.mark.asyncio
    async def test_handle_reload_provider_config_returns_not_implemented(self):
        from orb.interface.system_command_handlers import handle_reload_provider_config

        result = await handle_reload_provider_config(_ns())

        assert isinstance(result, dict)
        assert result.get("error") == "Not implemented"

    @pytest.mark.asyncio
    async def test_handle_execute_provider_operation_returns_not_implemented(self):
        from orb.interface.system_command_handlers import handle_execute_provider_operation

        result = await handle_execute_provider_operation(_ns())

        assert isinstance(result, dict)
        assert result.get("error") == "Not implemented"


# ---------------------------------------------------------------------------
# CQRS handlers — assert correct query type dispatched
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleProviderHealth:
    @pytest.mark.asyncio
    async def test_dispatches_get_system_status_query(self):
        from orb.application.queries.system import GetSystemStatusQuery
        from orb.interface.system_command_handlers import handle_provider_health

        container, query_bus = _mock_container_with_query_bus(query_return={"status": "ok"})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_provider_health(_ns())

        query_bus.execute.assert_awaited_once()
        assert isinstance(query_bus.execute.call_args[0][0], GetSystemStatusQuery)
        assert isinstance(result, dict)
        assert "health" in result


@pytest.mark.unit
class TestHandleProviderConfig:
    @pytest.mark.asyncio
    async def test_dispatches_get_provider_config_query(self):
        from orb.application.queries.system import GetProviderConfigQuery
        from orb.interface.system_command_handlers import handle_provider_config

        container, query_bus = _mock_container_with_query_bus(query_return={"provider": "aws"})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_provider_config(_ns())

        query_bus.execute.assert_awaited_once()
        assert isinstance(query_bus.execute.call_args[0][0], GetProviderConfigQuery)
        assert isinstance(result, dict)
        assert "config" in result


@pytest.mark.unit
class TestHandleProviderMetrics:
    @pytest.mark.asyncio
    async def test_dispatches_get_provider_metrics_query_with_provider_name(self):
        from orb.application.provider.queries import GetProviderMetricsQuery
        from orb.interface.system_command_handlers import handle_provider_metrics

        container, query_bus = _mock_container_with_query_bus(query_return={"latency_ms": 42})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_provider_metrics(_ns(provider="aws"))

        query_bus.execute.assert_awaited_once()
        q = query_bus.execute.call_args[0][0]
        assert isinstance(q, GetProviderMetricsQuery)
        assert q.provider_name == "aws"
        assert "metrics" in result

    @pytest.mark.asyncio
    async def test_dispatches_with_no_provider_name(self):
        from orb.application.provider.queries import GetProviderMetricsQuery
        from orb.interface.system_command_handlers import handle_provider_metrics

        container, query_bus = _mock_container_with_query_bus(query_return={})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            await handle_provider_metrics(_ns())

        q = query_bus.execute.call_args[0][0]
        assert isinstance(q, GetProviderMetricsQuery)
        assert q.provider_name is None


@pytest.mark.unit
class TestHandleSystemStatus:
    @pytest.mark.asyncio
    async def test_dispatches_get_system_status_query_with_flags(self):
        from orb.application.queries.system import GetSystemStatusQuery
        from orb.interface.system_command_handlers import handle_system_status

        container, query_bus = _mock_container_with_query_bus(query_return={"healthy": True})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_system_status(_ns(detailed=True))

        query_bus.execute.assert_awaited_once()
        q = query_bus.execute.call_args[0][0]
        assert isinstance(q, GetSystemStatusQuery)
        assert q.include_provider_health is True
        assert q.detailed is True
        assert "system_status" in result

    @pytest.mark.asyncio
    async def test_detailed_defaults_to_false_when_not_set(self):
        from orb.application.queries.system import GetSystemStatusQuery
        from orb.interface.system_command_handlers import handle_system_status

        container, query_bus = _mock_container_with_query_bus(query_return={})

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            await handle_system_status(_ns())

        q = query_bus.execute.call_args[0][0]
        assert isinstance(q, GetSystemStatusQuery)
        assert q.detailed is False


# ---------------------------------------------------------------------------
# handle_list_providers — uses ConfigurationPort via container
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleListProviders:
    @pytest.mark.asyncio
    async def test_returns_providers_from_config_port(self):
        from orb.interface.system_command_handlers import handle_list_providers

        mock_provider = MagicMock()
        mock_provider.name = "aws-default"
        mock_provider.type = "aws"
        mock_provider.config = {"region": "us-east-1"}
        mock_provider.enabled = True
        mock_provider.weight = 1
        mock_provider.priority = 1
        mock_provider.get_effective_handlers.return_value = {"machines": MagicMock()}

        mock_provider_config = MagicMock()
        mock_provider_config.get_active_providers.return_value = [mock_provider]
        mock_provider_config.provider_defaults = {}
        mock_provider_config.selection_policy = "round-robin"

        mock_config_port = MagicMock()
        mock_config_port.get_provider_config.return_value = mock_provider_config

        container = MagicMock()
        container.get.return_value = mock_config_port

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_list_providers(_ns())

        assert result["count"] == 1
        assert result["providers"][0]["name"] == "aws-default"
        assert result["providers"][0]["type"] == "aws"

    @pytest.mark.asyncio
    async def test_no_provider_config_returns_empty_list(self):
        from orb.interface.system_command_handlers import handle_list_providers

        mock_config_port = MagicMock()
        mock_config_port.get_provider_config.return_value = None

        container = MagicMock()
        container.get.return_value = mock_config_port

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_list_providers(_ns())

        assert result["count"] == 0
        assert result["providers"] == []

    @pytest.mark.asyncio
    async def test_exception_returns_error_dict(self):
        from orb.interface.system_command_handlers import handle_list_providers

        container = MagicMock()
        container.get.side_effect = RuntimeError("container exploded")

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_list_providers(_ns())

        assert result["count"] == 0
        assert "error" in result


# ---------------------------------------------------------------------------
# handle_system_health — delegates to handle_health_check via executor
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleSystemHealth:
    @pytest.mark.asyncio
    async def test_returns_success_when_health_check_returns_0(self):
        from orb.interface.system_command_handlers import handle_system_health

        with patch(
            "orb.interface.health_command_handler.handle_health_check", return_value=0
        ) as mock_hc:
            result = await handle_system_health(_ns())

        mock_hc.assert_called_once()
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_returns_error_when_health_check_returns_nonzero(self):
        from orb.interface.system_command_handlers import handle_system_health

        with patch("orb.interface.health_command_handler.handle_health_check", return_value=1):
            result = await handle_system_health(_ns())

        assert result["status"] == "error"


# ---------------------------------------------------------------------------
# handle_system_metrics — uses MetricsCollector via container.get_optional
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleSystemMetrics:
    @pytest.mark.asyncio
    async def test_returns_metrics_when_collector_available(self):
        from orb.interface.system_command_handlers import handle_system_metrics

        mock_metrics = MagicMock()
        mock_metrics.get_metrics.return_value = {"requests_total": 5}

        container = MagicMock()
        container.get_optional.return_value = mock_metrics

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_system_metrics(_ns())

        assert result["metrics"] == {"requests_total": 5}

    @pytest.mark.asyncio
    async def test_returns_empty_metrics_when_collector_unavailable(self):
        from orb.interface.system_command_handlers import handle_system_metrics

        container = MagicMock()
        container.get_optional.return_value = None

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_system_metrics(_ns())

        assert result["metrics"] == {}

    @pytest.mark.asyncio
    async def test_returns_error_dict_when_get_metrics_raises(self):
        from orb.interface.system_command_handlers import handle_system_metrics

        mock_metrics = MagicMock()
        mock_metrics.get_metrics.side_effect = RuntimeError("metrics broken")

        container = MagicMock()
        container.get_optional.return_value = mock_metrics

        with patch("orb.interface.system_command_handlers.get_container", return_value=container):
            result = await handle_system_metrics(_ns())

        assert result["metrics"] == {}
        assert "error" in result


# ---------------------------------------------------------------------------
# handle_select_provider_strategy — reads args.provider, no bus
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHandleSelectProviderStrategy:
    @pytest.mark.asyncio
    async def test_returns_selected_provider_from_args(self):
        from orb.interface.system_command_handlers import handle_select_provider_strategy

        with patch("orb.providers.registry.get_provider_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_registered_providers.return_value = ["aws"]
            mock_registry_fn.return_value = mock_registry

            result = await handle_select_provider_strategy(_ns(provider="gcp"))

        assert result["result"]["selected_provider"] == "gcp"

    @pytest.mark.asyncio
    async def test_falls_back_to_first_registered_provider_when_no_args(self):
        from orb.interface.system_command_handlers import handle_select_provider_strategy

        with patch("orb.providers.registry.get_provider_registry") as mock_registry_fn:
            mock_registry = MagicMock()
            mock_registry.get_registered_providers.return_value = ["aws"]
            mock_registry_fn.return_value = mock_registry

            result = await handle_select_provider_strategy(_ns())

        assert result["result"]["selected_provider"] == "aws"

    @pytest.mark.asyncio
    async def test_falls_back_to_aws_when_registry_raises(self):
        from orb.interface.system_command_handlers import handle_select_provider_strategy

        with patch(
            "orb.providers.registry.get_provider_registry",
            side_effect=RuntimeError("registry unavailable"),
        ):
            result = await handle_select_provider_strategy(_ns())

        assert result["result"]["selected_provider"] == "aws"
