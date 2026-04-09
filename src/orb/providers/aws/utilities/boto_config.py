"""Boto3 configuration utilities for AWS provider."""

from typing import Any, Optional

from orb.infrastructure.logging.logger import get_logger
from orb.infrastructure.utilities.network_utils import STANDARD_TIMEOUT, TimeoutConfig

logger = get_logger(__name__)


def get_boto3_config(
    timeout: Optional[TimeoutConfig] = None, max_retries: int = 3, **kwargs: Any
) -> Any:
    """Get boto3 Config object with timeout settings.

    Args:
        timeout: Timeout configuration
        max_retries: Maximum number of retries
        **kwargs: Additional config parameters

    Returns:
        boto3.Config object
    """
    try:
        from botocore.config import Config
    except ImportError:
        logger.warning("botocore not available, returning None config", exc_info=True)
        return None

    timeout_config = timeout or STANDARD_TIMEOUT

    config_params = {
        "connect_timeout": timeout_config.connect,
        "read_timeout": timeout_config.read,
        "retries": {"max_attempts": max_retries, "mode": "adaptive"},
        **kwargs,
    }

    return Config(**config_params)
