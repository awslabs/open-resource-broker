#!/bin/bash
# dev-tools/unified/unified_publisher.sh
# Unified publisher for containers and documentation
set -e

echo "=== UNIFIED PUBLISHER ==="
echo "Publishing containers and documentation..."

# Build and push containers
if [ "${PUBLISH_CONTAINERS:-false}" = "true" ]; then
    echo "=== PUBLISHING CONTAINERS ==="
    echo "Building and pushing multi-platform containers..."
    make container-push-multi
    echo "✅ Container publishing complete"
else
    echo "⏭️  Skipping container publishing (PUBLISH_CONTAINERS not set to true)"
fi

# Deploy documentation
if [ "${PUBLISH_DOCS:-false}" = "true" ]; then
    echo "=== PUBLISHING DOCUMENTATION ==="
    echo "Deploying documentation to GitHub Pages..."
    make ci-docs-deploy
    echo "✅ Documentation publishing complete"
else
    echo "⏭️  Skipping documentation publishing (PUBLISH_DOCS not set to true)"
fi

echo "=== UNIFIED PUBLISHER COMPLETE ==="
echo
echo "To enable publishing:"
echo "  PUBLISH_CONTAINERS=true PUBLISH_DOCS=true ./unified_publisher.sh"
