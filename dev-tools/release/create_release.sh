#!/bin/bash
# dev-tools/release/create_release.sh
# Simple wrapper around semantic-release for different release types
set -e

BUMP_TYPE="${1:-patch}"
PRE_RELEASE="${2:-}"

echo "=== CREATE RELEASE ==="
echo "Bump type: $BUMP_TYPE"
echo "Pre-release: ${PRE_RELEASE:-none}"

# Use semantic-release with appropriate flags
if [ -n "$PRE_RELEASE" ]; then
    echo "Creating prerelease with semantic-release..."
    uv run python-semantic-release version --prerelease
else
    echo "Creating stable release with semantic-release..."
    uv run python-semantic-release version
fi

echo "Release creation complete"
