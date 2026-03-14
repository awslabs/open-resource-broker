"""Metrics event handler — records provisioning metrics on domain events."""

import time
from typing import Optional

from orb.application.events.base.event_handler import EventHandler
from orb.domain.base.events import DomainEvent
from orb.domain.base.ports import LoggingPort
from orb.monitoring.metrics import MetricsCollector


class MetricsEventHandler(EventHandler):
    """
    Subscribes to provisioning domain events and updates MetricsCollector.

    Handles:
    - RequestCreatedEvent  -> increments pending_requests gauge
    - RequestCompletedEvent -> increments requests_total, sets active_instances,
                               records provisioning_duration
    - RequestFailedEvent   -> increments requests_failed_total
    """

    def __init__(
        self,
        collector: MetricsCollector,
        logger: Optional[LoggingPort] = None,
    ) -> None:
        super().__init__(logger)
        self._collector = collector
        # Track when requests were created so we can record duration on completion
        self._request_start_times: dict[str, float] = {}

    async def process_event(self, event: DomainEvent) -> None:
        """Route event to the appropriate metrics update."""
        event_type = event.event_type

        if event_type == "RequestCreatedEvent":
            self._handle_request_created(event)
        elif event_type == "RequestCompletedEvent":
            self._handle_request_completed(event)
        elif event_type == "RequestFailedEvent":
            self._handle_request_failed(event)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _handle_request_created(self, event: DomainEvent) -> None:
        request_id = getattr(event, "request_id", event.aggregate_id)
        self._request_start_times[request_id] = time.time()
        # Increment pending_requests by 1 each time a request is created
        current = self._collector.metrics.get("pending_requests")
        new_value = (current.value + 1.0) if current is not None else 1.0
        self._collector.set_gauge("pending_requests", new_value)

    def _handle_request_completed(self, event: DomainEvent) -> None:
        self._collector.increment_counter("requests_total")

        machine_ids: list[str] = getattr(event, "machine_ids", [])
        self._collector.set_gauge("active_instances", float(len(machine_ids)))

        # Record provisioning duration if we saw the corresponding created event
        request_id = getattr(event, "request_id", event.aggregate_id)
        start = self._request_start_times.pop(request_id, None)
        if start is not None:
            self._collector.record_time("provisioning_duration", time.time() - start)

        # Decrement pending_requests
        current = self._collector.metrics.get("pending_requests")
        if current is not None and current.value > 0:
            self._collector.set_gauge("pending_requests", current.value - 1.0)

    def _handle_request_failed(self, event: DomainEvent) -> None:
        self._collector.increment_counter("requests_failed_total")

        # Clean up start time tracking
        request_id = getattr(event, "request_id", event.aggregate_id)
        self._request_start_times.pop(request_id, None)

        # Decrement pending_requests
        current = self._collector.metrics.get("pending_requests")
        if current is not None and current.value > 0:
            self._collector.set_gauge("pending_requests", current.value - 1.0)
