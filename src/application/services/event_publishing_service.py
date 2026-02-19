"""Event publishing service for centralizing event publishing logic."""

from domain.base.events import RequestCompletedEvent, RequestCreatedEvent
from domain.base.ports.event_publisher_port import EventPublisherPort
from domain.request.aggregate import Request


class EventPublishingService:
    """Centralized event publishing service."""

    def __init__(self, event_publisher: EventPublisherPort):
        self._event_publisher = event_publisher

    async def publish_request_created(self, request: Request) -> None:
        """Publish request created event."""
        event = RequestCreatedEvent(
            request_id=request.request_id,
            template_id=request.template_id,
            machine_count=request.machine_count,
            provider_api=request.provider_api,
            status=request.status,
        )
        await self._event_publisher.publish(event)

    async def publish_request_completed(self, request: Request) -> None:
        """Publish request completed event."""
        event = RequestCompletedEvent(
            request_id=request.request_id,
            template_id=request.template_id,
            machine_count=request.machine_count,
            provider_api=request.provider_api,
            status=request.status,
            machine_ids=request.machine_ids,
            resource_ids=request.resource_ids,
        )
        await self._event_publisher.publish(event)
