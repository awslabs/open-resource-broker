"""Cloud account port - focused interface for account operations."""

from abc import ABC, abstractmethod


class CloudAccountPort(ABC):
    """Focused port for cloud account operations.

    This interface follows ISP by providing only account-related operations,
    allowing clients that only need account information to depend on a minimal interface.
    """

    @abstractmethod
    def get_account_id(self) -> str:
        """Get the current account identifier.

        Returns:
            Account identifier

        Raises:
            AuthorizationError: If credentials are invalid
            InfrastructureError: For other infrastructure errors
        """

    @abstractmethod
    def validate_credentials(self) -> bool:
        """Validate the current credentials.

        Returns:
            True if credentials are valid, False otherwise

        Raises:
            InfrastructureError: For infrastructure errors
        """
