"""Tests for BaseSchedulerStrategy utility methods."""

from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from infrastructure.scheduler.default.default_strategy import DefaultSchedulerStrategy


def make_strategy():
    """Return a DefaultSchedulerStrategy (concrete subclass of Base) with no DI."""
    return DefaultSchedulerStrategy()


class TestCoerceToDict:
    """Tests for BaseSchedulerStrategy._coerce_to_dict."""

    def test_plain_dict_returned_unchanged(self):
        d = {"a": 1, "b": 2}
        result = DefaultSchedulerStrategy._coerce_to_dict(d)
        assert result == {"a": 1, "b": 2}

    def test_model_dump_object(self):
        obj = MagicMock()
        obj.model_dump.return_value = {"x": 10}
        # model_dump takes priority over to_dict
        obj.to_dict.return_value = {"y": 20}
        result = DefaultSchedulerStrategy._coerce_to_dict(obj)
        assert result == {"x": 10}
        obj.model_dump.assert_called_once()

    def test_to_dict_object(self):
        obj = MagicMock(spec=["to_dict"])  # no model_dump
        obj.to_dict.return_value = {"z": 99}
        result = DefaultSchedulerStrategy._coerce_to_dict(obj)
        assert result == {"z": 99}

    def test_iterable_of_pairs(self):
        pairs = [("key1", "val1"), ("key2", "val2")]
        result = DefaultSchedulerStrategy._coerce_to_dict(pairs)
        assert result == {"key1": "val1", "key2": "val2"}

    def test_fallback_returns_empty_dict(self):
        # An integer cannot be coerced to a dict
        result = DefaultSchedulerStrategy._coerce_to_dict(42)
        assert result == {}


class TestUnwrapRequestId:
    """Tests for BaseSchedulerStrategy._unwrap_request_id."""

    def test_none_returns_none(self):
        assert DefaultSchedulerStrategy._unwrap_request_id(None) is None

    def test_plain_string_returned_as_string(self):
        assert DefaultSchedulerStrategy._unwrap_request_id("req-123") == "req-123"

    def test_dict_with_value_key(self):
        assert DefaultSchedulerStrategy._unwrap_request_id({"value": "req-abc"}) == "req-abc"

    def test_object_with_value_attr(self):
        obj = MagicMock(spec=["value"])
        obj.value = "req-obj-456"
        assert DefaultSchedulerStrategy._unwrap_request_id(obj) == "req-obj-456"

    def test_integer_converted_to_string(self):
        assert DefaultSchedulerStrategy._unwrap_request_id(7) == "7"

    def test_dict_without_value_key_converted_to_string(self):
        # A dict without "value" key falls through to str()
        result = DefaultSchedulerStrategy._unwrap_request_id({"id": "x"})
        assert isinstance(result, str)


class TestApplyTemplateDefaults:
    """Tests for BaseSchedulerStrategy._apply_template_defaults."""

    def test_returns_unchanged_when_service_is_none(self):
        strategy = make_strategy()
        strategy._template_defaults_service = cast(None, None)
        # Patch is_container_ready so the lazy property stays None
        with patch("infrastructure.di.container.is_container_ready", return_value=False):
            template = {"template_id": "t1", "image_id": "ami-123"}
            result = strategy._apply_template_defaults(template, "my-provider")
        assert result == template

    def test_delegates_to_service_when_present(self):
        strategy = make_strategy()
        mock_service = MagicMock()
        mock_service.resolve_template_defaults.return_value = {"template_id": "t1", "subnet_ids": ["s-1"]}
        strategy._template_defaults_service = cast(None, mock_service)

        template = {"template_id": "t1"}
        result = strategy._apply_template_defaults(template, "my-provider")

        mock_service.resolve_template_defaults.assert_called_once_with(template, "my-provider")
        assert result == {"template_id": "t1", "subnet_ids": ["s-1"]}


class TestTemplateDefaultsServiceProperty:
    """Tests for BaseSchedulerStrategy.template_defaults_service lazy property."""

    def test_returns_none_when_container_not_ready(self):
        strategy = make_strategy()
        with patch("infrastructure.di.container.is_container_ready", return_value=False):
            assert strategy.template_defaults_service is None

    def test_returns_service_when_container_ready(self):
        strategy = make_strategy()
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.get_optional.return_value = mock_service

        with patch("infrastructure.di.container.is_container_ready", return_value=True), \
             patch("infrastructure.di.container.get_container", return_value=mock_container):
            result = strategy.template_defaults_service

        assert result is mock_service

    def test_caches_service_after_first_resolution(self):
        strategy = make_strategy()
        mock_service = MagicMock()
        mock_container = MagicMock()
        mock_container.get_optional.return_value = mock_service

        with patch("infrastructure.di.container.is_container_ready", return_value=True), \
             patch("infrastructure.di.container.get_container", return_value=mock_container):
            first = strategy.template_defaults_service
            second = strategy.template_defaults_service

        assert first is second
        assert mock_container.get_optional.call_count == 1
