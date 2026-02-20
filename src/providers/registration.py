"""Provider registration functions."""


def register_all_provider_types() -> None:
    """Register all available provider types."""
    from providers.registry import get_provider_registry

    registry = get_provider_registry()

    # Register AWS provider
    from providers.aws.registration import register_aws_provider

    register_aws_provider(registry)

    # Future providers would be added here
    # register_provider1_provider(registry)
    # register_provider2_provider(registry)
