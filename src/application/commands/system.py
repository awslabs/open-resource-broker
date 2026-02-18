"""System-level commands for administrative operations."""

from typing import Optional

from application.dto.base import BaseCommand

# ============================================================================
# Provider Configuration Management Commands
# ============================================================================


class ReloadProviderConfigCommand(BaseCommand):
    """Command to reload provider configuration from file."""

    config_path: Optional[str] = None


class RefreshTemplatesCommand(BaseCommand):
    """Command to refresh templates from all sources."""

    provider_name: Optional[str] = None


class SetConfigurationCommand(BaseCommand):
    """Command to set configuration value."""

    key: str
    value: str


class TestStorageCommand(BaseCommand):
    """Command to test storage connectivity and functionality."""

    storage_type: Optional[str] = None


class MCPValidateCommand(BaseCommand):
    """Command to validate MCP server configuration and tools."""

    pass
