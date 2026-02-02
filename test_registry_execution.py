#!/usr/bin/env python3
"""Test script to verify Provider Registry can execute operations directly."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_registry_execution():
    """Test Provider Registry direct operation execution."""
    from providers.registry import get_provider_registry
    from providers.base.strategy.provider_strategy import ProviderOperation, ProviderOperationType
    from providers.aws.registration import register_aws_provider
    from infrastructure.adapters.logging_adapter import LoggingAdapter
    
    # Setup
    registry = get_provider_registry()
    logger = LoggingAdapter()
    registry.set_dependencies(logger)
    
    # Register AWS provider
    register_aws_provider(registry, logger)
    
    # Test provider capabilities with proper config
    print("Testing provider capabilities...")
    aws_config = {
        "region": "us-east-1",
        "profile": "default"
    }
    capabilities = registry.get_strategy_capabilities("aws", aws_config)
    if capabilities:
        print(f"✅ AWS capabilities: {capabilities.supported_apis}")
    else:
        print("❌ Failed to get AWS capabilities")
        return
    
    # Test health check operation
    print("\nTesting health check operation...")
    health_operation = ProviderOperation(
        operation_type=ProviderOperationType.HEALTH_CHECK,
        parameters={}
    )
    
    # Create minimal AWS config for testing
    aws_config = {
        "region": "us-east-1",
        "profile": "default"
    }
    
    result = await registry.execute_operation("aws", health_operation, aws_config)
    if result.success:
        print(f"✅ Health check successful: {result.data}")
    else:
        print(f"❌ Health check failed: {result.error_message}")
    
    # Test convenience method
    print("\nTesting convenience method...")
    try:
        # This should fail gracefully since we don't have real AWS credentials
        machine_result = await registry.create_machines(
            provider_identifier="aws",
            template_id="test-template",
            count=1,
            config=aws_config
        )
        print(f"Machine creation result: success={machine_result.success}")
        if not machine_result.success:
            print(f"Expected error: {machine_result.error_message}")
    except Exception as e:
        print(f"Exception during machine creation (expected): {e}")
    
    print("\n✅ Registry execution test completed!")

if __name__ == "__main__":
    asyncio.run(test_registry_execution())