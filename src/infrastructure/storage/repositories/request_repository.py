"""Single request repository implementation using storage strategy composition."""

import time
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from domain.base.events import (
    DomainEvent,
    RepositoryOperationCompletedEvent,
    RepositoryOperationFailedEvent,
    RepositoryOperationStartedEvent,
    SlowQueryDetectedEvent,
)
from domain.base.ports.storage_port import StoragePort
from domain.request.aggregate import Request
from domain.request.repository import RequestRepository as RequestRepositoryInterface
from domain.request.value_objects import RequestId, RequestStatus, RequestType
from infrastructure.error.decorators import handle_infrastructure_exceptions
from infrastructure.logging.logger import get_logger


class RequestSerializer:
    """Handles Request aggregate serialization/deserialization."""

    def to_dict(self, request: Request) -> dict[str, Any]:
        """Convert Request to storage format using domain serialization."""
        from infrastructure.utilities.common.serialization import process_value_objects
        
        data = request.model_dump()
        data = process_value_objects(data)
        data["schema_version"] = "2.0.0"
        return data
    
    def from_dict(self, data: dict[str, Any]) -> Request:
        """Convert storage format to Request using domain validation."""
        return Request.model_validate(data)


class RequestRepositoryImpl(RequestRepositoryInterface):
    """Single request repository implementation using storage strategy composition."""

    def __init__(self, storage_port: StoragePort, event_publisher=None) -> None:
        """Initialize repository with storage port and optional event publisher."""
        self.storage_port = storage_port
        self.serializer = RequestSerializer()
        self.logger = get_logger(__name__)
        self.event_publisher = event_publisher
        self.slow_query_threshold_ms = 1000.0  # 1 second threshold

    def _publish_storage_event(self, event: DomainEvent) -> None:
        """Publish storage event if publisher is available."""
        if self.event_publisher:
            try:
                self.event_publisher.publish(event)
            except Exception as e:
                self.logger.warning("Failed to publish storage event: %s", e)

    @handle_infrastructure_exceptions(context="request_repository_save")
    def save(self, request: Request) -> list[Any]:
        """Save request using storage strategy and return extracted events."""
        operation_id = str(uuid4())
        start_time = time.time()
        entity_id = str(request.request_id.value)

        # Publish operation started event
        self._publish_storage_event(
            RepositoryOperationStartedEvent(
                aggregate_id=operation_id,
                aggregate_type="RepositoryOperation",
                operation_id=operation_id,
                entity_type="Request",
                entity_id=entity_id,
                storage_strategy=self.storage_port.__class__.__name__,
                operation_type="save",
            )
        )

        try:
            # Save the request
            request_data = self.serializer.to_dict(request)
            self.storage_port.save(entity_id, request_data)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Extract events from the aggregate
            events = request.get_domain_events()
            request.clear_domain_events()

            # Publish operation completed event
            self._publish_storage_event(
                RepositoryOperationCompletedEvent(
                    aggregate_id=operation_id,
                    aggregate_type="RepositoryOperation",
                    operation_id=operation_id,
                    entity_type="Request",
                    entity_id=entity_id,
                    storage_strategy=self.storage_port.__class__.__name__,
                    operation_type="save",
                    duration_ms=duration_ms,
                    success=True,
                    records_affected=1,
                )
            )

            # Check for slow operations
            if duration_ms > self.slow_query_threshold_ms:
                self._publish_storage_event(
                    SlowQueryDetectedEvent(
                        aggregate_id=operation_id,
                        aggregate_type="Performance",
                        operation_id=operation_id,
                        entity_type="Request",
                        entity_id=entity_id,
                        storage_strategy=self.storage_port.__class__.__name__,
                        operation_type="save",
                        duration_ms=duration_ms,
                        threshold_ms=self.slow_query_threshold_ms,
                        query_details={"data_size": len(str(request_data))},
                    )
                )

            self.logger.debug(
                "Saved request %s and extracted %s events",
                request.request_id,
                len(events),
            )
            return events

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            # Publish operation failed event
            self._publish_storage_event(
                RepositoryOperationFailedEvent(
                    aggregate_id=operation_id,
                    aggregate_type="RepositoryOperation",
                    operation_id=operation_id,
                    entity_type="Request",
                    entity_id=entity_id,
                    storage_strategy=self.storage_port.__class__.__name__,
                    operation_type="save",
                    error_message=str(e),
                    error_code=type(e).__name__,
                    retry_count=0,
                    duration_ms=duration_ms,
                )
            )

            self.logger.error("Failed to save request %s: %s", request.request_id, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_get_by_id")
    def get_by_id(self, request_id: RequestId) -> Optional[Request]:
        """Get request by ID using storage strategy."""
        try:
            data = self.storage_port.find_by_id(str(request_id.value))
            if data:
                return self.serializer.from_dict(data)
            return None
        except Exception as e:
            self.logger.error("Failed to get request %s: %s", request_id, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_by_id")
    def find_by_id(self, request_id: RequestId | str) -> Optional[Request]:
        """Find request by ID (alias for get_by_id)."""
        # Convert string to RequestId if needed
        if isinstance(request_id, str):
            request_id = RequestId(value=request_id)
        return self.get_by_id(request_id)

    @handle_infrastructure_exceptions(context="request_repository_find_by_request_id")
    def find_by_request_id(self, request_id: str) -> Optional[Request]:
        """Find request by request ID string."""
        try:
            return self.get_by_id(RequestId(value=request_id))
        except Exception as e:
            self.logger.error("Failed to find request by request_id %s: %s", request_id, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_by_status")
    def find_by_status(self, status: RequestStatus) -> list[Request]:
        """Find requests by status."""
        try:
            criteria = {"status": status.value}
            data_list = self.storage_port.find_by_criteria(criteria)
            return [self.serializer.from_dict(data) for data in data_list]
        except Exception as e:
            self.logger.error("Failed to find requests by status %s: %s", status, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_by_template_id")
    def find_by_template_id(self, template_id: str) -> list[Request]:
        """Find requests by template ID."""
        try:
            criteria = {"template_id": template_id}
            data_list = self.storage_port.find_by_criteria(criteria)
            return [self.serializer.from_dict(data) for data in data_list]
        except Exception as e:
            self.logger.error("Failed to find requests by template_id %s: %s", template_id, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_by_type")
    def find_by_type(self, request_type: RequestType) -> list[Request]:
        """Find requests by type."""
        try:
            criteria = {"request_type": request_type.value}
            data_list = self.storage_port.find_by_criteria(criteria)
            return [self.serializer.from_dict(data) for data in data_list]
        except Exception as e:
            self.logger.error("Failed to find requests by type %s: %s", request_type, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_pending_requests")
    def find_pending_requests(self) -> list[Request]:
        """Find pending requests."""
        return self.find_by_status(RequestStatus.PENDING)

    @handle_infrastructure_exceptions(context="request_repository_find_active_requests")
    def find_active_requests(self) -> list[Request]:
        """Find active requests (pending or in_progress)."""
        try:
            pending = self.find_by_status(RequestStatus.PENDING)
            in_progress = self.find_by_status(RequestStatus.IN_PROGRESS)
            return pending + in_progress
        except Exception as e:
            self.logger.error("Failed to find active requests: %s", e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_by_date_range")
    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> list[Request]:
        """Find requests within date range."""
        try:
            all_requests = self.find_all()
            filtered_requests = []

            for request in all_requests:
                if start_date <= request.created_at <= end_date:
                    filtered_requests.append(request)

            return filtered_requests
        except Exception as e:
            self.logger.error("Failed to find requests by date range: %s", e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_find_all")
    def find_all(self) -> list[Request]:
        """Find all requests."""
        try:
            all_data = self.storage_port.find_all()
            return [self.serializer.from_dict(data) for data in all_data.values()]
        except Exception as e:
            self.logger.error("Failed to find all requests: %s", e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_delete")
    def delete(self, request_id: RequestId) -> None:
        """Delete request by ID."""
        try:
            self.storage_port.delete(str(request_id.value))
            self.logger.debug("Deleted request %s", request_id)
        except Exception as e:
            self.logger.error("Failed to delete request %s: %s", request_id, e)
            raise

    @handle_infrastructure_exceptions(context="request_repository_exists")
    def exists(self, request_id: RequestId) -> bool:
        """Check if request exists."""
        try:
            return self.storage_port.exists(str(request_id.value))
        except Exception as e:
            self.logger.error("Failed to check if request %s exists: %s", request_id, e)
            raise
