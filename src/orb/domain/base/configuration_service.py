"""Domain service for translating ConfigurationPort data into domain-meaningful values."""

from orb.domain.base.ports.configuration_port import ConfigurationPort
from orb.domain.constants import (
    REQUEST_ID_PATTERN,
    REQUEST_ID_PREFIX_ACQUIRE,
    REQUEST_ID_PREFIX_RETURN,
)


class DomainConfigurationService:
    """Translates raw config dicts from ConfigurationPort into typed, domain-meaningful values.

    Handlers depend on this service, not on the raw dict structure.
    """

    def __init__(self, config_port: ConfigurationPort) -> None:
        self._config_port = config_port

    def get_acquire_request_prefix(self) -> str:
        """Return the configured prefix for ACQUIRE request IDs."""
        prefixes = self._config_port.get_naming_config().get("prefixes", {})
        return str(prefixes.get("request", REQUEST_ID_PREFIX_ACQUIRE))

    def get_return_request_prefix(self) -> str:
        """Return the configured prefix for RETURN request IDs."""
        prefixes = self._config_port.get_naming_config().get("prefixes", {})
        return str(prefixes.get("return", REQUEST_ID_PREFIX_RETURN))

    def get_request_id_pattern(self) -> str:
        """Return the regex pattern for validating request IDs."""
        patterns = self._config_port.get_naming_config().get("patterns", {})
        return str(patterns.get("request_id", REQUEST_ID_PATTERN))
