"""Tests for the SSE stream endpoint on the requests router."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from orb.api.dependencies import get_request_status_handler
from orb.api.routers.requests import router as requests_router


@pytest.fixture()
def requests_app():
    app = FastAPI()
    app.include_router(requests_router)
    return app


def _make_handler_returning(*statuses):
    """Return a handler whose handle() yields successive status dicts."""
    handler = MagicMock()
    side_effects = []
    for status in statuses:
        result = {"requests": [{"requestId": "req-stream-1", "status": status}]}
        side_effects.append(result)
    handler.handle = AsyncMock(side_effect=side_effects)
    return handler


def _collect_sse_lines(response) -> list[dict]:
    """Parse SSE data lines from a streaming response into a list of dicts."""
    parsed = []
    for raw in response.iter_lines():
        line = raw if isinstance(raw, str) else raw.decode()
        if line.startswith("data: "):
            payload = line[len("data: ") :]
            try:
                obj = json.loads(payload)
                if obj:
                    parsed.append(obj)
            except json.JSONDecodeError:
                pass  # Malformed SSE lines are intentionally skipped
    return parsed


@pytest.mark.unit
@pytest.mark.api
class TestStreamEndpoint:
    """Tests for GET /{request_id}/stream SSE endpoint."""

    def _make_client(self, app, handler):
        app.dependency_overrides[get_request_status_handler] = lambda: handler
        # Use a short interval so the test doesn't actually sleep
        return TestClient(app, raise_server_exceptions=False)

    def test_happy_path_sse_data_lines_format(self, requests_app):
        """SSE lines are prefixed with 'data: ' and contain valid JSON."""
        handler = _make_handler_returning("running", "completed")
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=30") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            lines = list(resp.iter_lines())

        data_lines = [
            l if isinstance(l, str) else l.decode()
            for l in lines
            if (l if isinstance(l, str) else l.decode()).startswith("data: ")
        ]
        assert len(data_lines) >= 1
        for line in data_lines:
            payload = line[len("data: ") :]
            # Must be valid JSON
            json.loads(payload)

    def test_stream_ends_on_completed_status(self, requests_app):
        """Stream closes after receiving COMPLETED terminal status."""
        handler = _make_handler_returning("running", "completed")
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=30") as resp:
            events = _collect_sse_lines(resp)

        statuses = [e["requests"][0]["status"] for e in events if e.get("requests")]
        assert "completed" in statuses
        # Handler should not be called more times than needed
        assert handler.handle.await_count <= 3

    def test_stream_ends_on_failed_status(self, requests_app):
        """Stream closes after receiving FAILED terminal status."""
        handler = _make_handler_returning("running", "failed")
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=30") as resp:
            events = _collect_sse_lines(resp)

        statuses = [e["requests"][0]["status"] for e in events if e.get("requests")]
        assert "failed" in statuses

    def test_stream_ends_on_cancelled_status(self, requests_app):
        """Stream closes after receiving CANCELLED terminal status."""
        handler = _make_handler_returning("pending", "cancelled")
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=30") as resp:
            events = _collect_sse_lines(resp)

        statuses = [e["requests"][0]["status"] for e in events if e.get("requests")]
        assert "cancelled" in statuses

    def test_stream_timeout_expiry(self, requests_app):
        """Stream closes after timeout even if no terminal status is reached."""
        # Always return non-terminal status
        handler = MagicMock()
        handler.handle = AsyncMock(
            return_value={"requests": [{"requestId": "req-stream-1", "status": "running"}]}
        )
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=1") as resp:
            assert resp.status_code == 200
            events = _collect_sse_lines(resp)

        # Stream must have closed; at least one event emitted before timeout
        assert len(events) >= 1
        # Handler called a bounded number of times (timeout / interval)
        assert handler.handle.await_count < 20

    def test_stream_error_mid_stream_closes_cleanly(self, requests_app):
        """When handler raises mid-stream, stream sends empty sentinel and closes."""
        handler = MagicMock()
        handler.handle = AsyncMock(side_effect=RuntimeError("provider unavailable"))
        client = self._make_client(requests_app, handler)

        with client.stream("GET", "/requests/req-stream-1/stream?interval=0.5&timeout=30") as resp:
            assert resp.status_code == 200
            raw_lines = [l if isinstance(l, str) else l.decode() for l in resp.iter_lines()]

        data_lines = [l for l in raw_lines if l.startswith("data: ")]
        # The error path yields exactly one sentinel "data: {}\n\n" then returns
        assert len(data_lines) == 1
        assert data_lines[0] == "data: {}"
        # Handler called exactly once before the error
        handler.handle.assert_awaited_once()
