"""Port for resolving application directory paths."""

from abc import ABC, abstractmethod


class PathResolutionPort(ABC):
    """Port for resolving application directory paths.

    Separates filesystem path resolution from configuration value access (ISP).
    Infrastructure adapters implement this backed by platform-specific logic.
    """

    @abstractmethod
    def get_config_dir(self) -> str:
        """Get the configuration directory path."""
        pass

    @abstractmethod
    def get_work_dir(self) -> str:
        """Get the work directory path."""
        pass

    @abstractmethod
    def get_logs_dir(self) -> str:
        """Get the logs directory path."""
        pass
