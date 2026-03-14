"""Thread-safe event handler that records domain events into MetricsCollector."""

import threading
import time

from orb.domain.base.events import DomainEvent
from orb.monitoring.metrics import MetricsCollector


class MetricsEventHandler:
    """Records request lifecycle events into a MetricsCollector in a thread-safe way."""

    def __init__(self, metrics_collector: MetricsCollector) -> None:
        """Initialize with a shared MetricsCollector."""
        self._collector = metrics_collector
        self._lock = threading.Lock()
        self._request_start_times: dict[str, float] = {}

    def on_request_started(self, event: DomainEvent) -> None:
        """Record the start time for a request."""
        request_id = str(getattr(event, "request_id", "") or event.metadata.get("request_id", ""))
        if not request_id:
            return
        with self._lock:
            self._request_start_times[request_id] = time.time()
        self._collector.increment_counter("requests_total")
        self._collector.increment_gauge("pending_requests")

    def on_request_completed(self, event: DomainEvent) -> None:
        """Record a successfully completed request."""
        request_id = str(getattr(event, "request_id", "") or event.metadata.get("request_id", ""))
        with self._lock:
            start_time = self._request_start_times.pop(request_id, None)
        if start_time is not None:
            self._collector.record_time("request_duration", time.time() - start_time)
        self._collector.decrement_gauge("pending_requests")

    def on_request_failed(self, event: DomainEvent) -> None:
        """Record a failed request."""
        request_id = str(getattr(event, "request_id", "") or event.metadata.get("request_id", ""))
        with self._lock:
            start_time = self._request_start_times.pop(request_id, None)
        if start_time is not None:
            self._collector.record_time("request_error_duration", time.time() - start_time)
        self._collector.increment_counter("requests_failed_total")
        self._collector.decrement_gauge("pending_requests")

    def on_aws_api_call(self, event: DomainEvent) -> None:
        """Record an AWS API call event."""
        success = bool(getattr(event, "success", True))
        self._collector.increment_counter("aws_api_calls_total")
        if not success:
            self._collector.increment_counter("aws_api_errors_total")

    def get_pending_request_count(self) -> int:
        """Return the number of in-flight requests (thread-safe snapshot)."""
        with self._lock:
            return len(self._request_start_times)
