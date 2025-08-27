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

log_info "Creating temporary branch from historical commit $COMMIT_HASH"
# Step 1: Checkout historical commit first (clean state)
git checkout -b "$TEMP_BRANCH" "$COMMIT_HASH" -q

log_info "Copying modern build system to historical code"
# Step 2: Copy modern build files (avoid conflicts by using current branch files)
git checkout "$CURRENT_BRANCH" -- Makefile dev-tools/ pyproject.toml 2>/dev/null || {
    log_warn "Some build files don't exist in current branch, continuing..."
}

# Step 3: Auto-resolve any conflicts by preferring modern build system
if ! git diff-index --quiet HEAD --; then
    log_info "Auto-resolving build system conflicts..."
    git add . 2>/dev/null || true
fi

# Step 4: Update version in the temporary branch
log_info "Setting version to $VERSION in historical context"
if [ -f ".project.yml" ]; then
    # Use modern version system if available
    echo "project:
  version: $VERSION" > .project.yml
elif [ -f "pyproject.toml" ]; then
    # Update pyproject.toml version
    sed -i.bak "s/^version = .*/version = \"$VERSION\"/" pyproject.toml && rm -f pyproject.toml.bak
fi

# Override VERSION for build
export VERSION="$VERSION"

# Step 5: Build with historical code + modern build system
log_info "Building historical release with modern build system"
IS_RELEASE=true make build 2>/dev/null || {
    log_error "Build failed - historical code may be incompatible with modern build system"
    git checkout "$CURRENT_BRANCH" -q
    git branch -D "$TEMP_BRANCH" -q 2>/dev/null || true
    exit 1
}

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
