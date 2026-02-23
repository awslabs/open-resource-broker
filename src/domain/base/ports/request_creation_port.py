"""Port for request creation operations."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from domain.request.aggregate import Request

if TYPE_CHECKING:
    from application.dto.commands import CreateRequestCommand
    from domain.base.results import ProviderSelectionResult
    from domain.template.template_aggregate import Template


class RequestCreationPort(ABC):
    """Port for creating request aggregates with validation and metadata."""

    @abstractmethod
    def create_machine_request(
        self,
        command: "CreateRequestCommand",
        template: "Template",
        selection_result: "ProviderSelectionResult",
    ) -> Request:
        """
        Create request aggregate with validation and metadata.

        Args:
            command: The create request command
            template: The template to use for the request
            selection_result: The provider selection result

        Returns:
            Request aggregate with proper metadata and provider information
        """
