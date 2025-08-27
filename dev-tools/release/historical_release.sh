#!/bin/bash
set -e

# Historical Release Script
# Creates releases for historical commits that may not have had working build infrastructure

COMMIT_HASH="$1"
VERSION="$2"
DRY_RUN="${DRY_RUN:-false}"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ -z "$COMMIT_HASH" ] || [ -z "$VERSION" ]; then
    echo "Usage: $0 <commit-hash> <version>"
    echo ""
    echo "Examples:"
    echo "  $0 abc123 0.0.1"
    echo "  DRY_RUN=true $0 abc123 0.0.1"
    exit 1
fi

log_info "Creating historical release $VERSION from commit $COMMIT_HASH"

if [ "$DRY_RUN" = "true" ]; then
    log_warn "[DRY RUN] Would create release $VERSION from $COMMIT_HASH"
    exit 0
fi

# Verify commit exists
if ! git rev-parse --verify "$COMMIT_HASH" >/dev/null 2>&1; then
    log_error "Commit $COMMIT_HASH does not exist"
    exit 1
fi

# Store current state
CURRENT_BRANCH=$(git branch --show-current)
TEMP_BRANCH="historical-release-$VERSION-$(date +%s)"

log_info "Creating temporary branch: $TEMP_BRANCH"
git checkout -b "$TEMP_BRANCH"

# Identify source files to extract from historical commit
SOURCE_DIRS="src tests README.md setup.py requirements.txt pyproject.toml"

log_info "Extracting source files from commit $COMMIT_HASH"
for item in $SOURCE_DIRS; do
    if git show "$COMMIT_HASH:$item" >/dev/null 2>&1; then
        log_info "  Extracting: $item"
        git checkout "$COMMIT_HASH" -- "$item" 2>/dev/null || true
    fi
done

# Create temporary version override
log_info "Setting version to $VERSION"
echo "project:
  version: $VERSION" > .temp_version.yml

# Override VERSION for build
export VERSION="$VERSION"

# Build release using current build infrastructure
log_info "Building release with current build system"
IS_RELEASE=true make build

# Tag the original commit (not our temporary branch)
log_info "Tagging original commit $COMMIT_HASH as v$VERSION"
git tag "v$VERSION" "$COMMIT_HASH"

# Cleanup
log_info "Cleaning up temporary branch"
git checkout "$CURRENT_BRANCH"
git branch -D "$TEMP_BRANCH"
rm -f .temp_version.yml

log_info "Historical release $VERSION created successfully!"
log_info "  - Built package with version $VERSION"
log_info "  - Tagged commit $COMMIT_HASH as v$VERSION"
log_info "  - Package ready for publishing"
