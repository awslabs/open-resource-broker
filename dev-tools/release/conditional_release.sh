#!/bin/bash
# dev-tools/release/conditional_release.sh
# Create releases conditionally based on existing tags
set -e

RELEASE_TYPE="${1:-alpha}"

echo "=== CONDITIONAL RELEASE ($RELEASE_TYPE) ==="

case "$RELEASE_TYPE" in
    "alpha")
        echo "Checking if alpha release is needed..."
        LAST_ALPHA=$(git tag -l "v*-alpha*" --sort=-version:refname | head -1 || echo "none")
        if [ "$LAST_ALPHA" = "none" ]; then
            COMMITS_SINCE=$(git rev-list --count HEAD)
        else
            COMMITS_SINCE=$(git rev-list --count ${LAST_ALPHA}..HEAD)
        fi
        
        if [ "$COMMITS_SINCE" -gt 0 ]; then
            echo "Found $COMMITS_SINCE commits since last alpha, creating release..."
            make release-patch-alpha
        else
            echo "No commits since last alpha, skipping"
        fi
        ;;
        
    "beta")
        echo "Checking if beta release is needed..."
        LAST_ALPHA=$(git tag -l "v*-alpha*" --sort=-version:refname | head -1 || echo "none")
        LAST_BETA=$(git tag -l "v*-beta*" --sort=-version:refname | head -1 || echo "none")
        
        if [ "$LAST_ALPHA" != "none" ]; then
            ALPHA_BASE=$(echo "$LAST_ALPHA" | sed 's/v\([0-9]*\.[0-9]*\.[0-9]*\)-.*/\1/')
            BETA_BASE="none"
            if [ "$LAST_BETA" != "none" ]; then
                BETA_BASE=$(echo "$LAST_BETA" | sed 's/v\([0-9]*\.[0-9]*\.[0-9]*\)-.*/\1/')
            fi
            
            if [ "$ALPHA_BASE" != "$BETA_BASE" ]; then
                echo "Promoting alpha $LAST_ALPHA to beta..."
                make release-patch-beta
            else
                echo "Beta already exists for version $ALPHA_BASE, skipping"
            fi
        else
            echo "No alpha releases found, skipping beta creation"
        fi
        ;;
        
    "rc")
        echo "Checking if RC release is needed..."
        LAST_BETA=$(git tag -l "v*-beta*" --sort=-version:refname | head -1 || echo "none")
        LAST_RC=$(git tag -l "v*-rc*" --sort=-version:refname | head -1 || echo "none")
        
        if [ "$LAST_BETA" != "none" ]; then
            BETA_BASE=$(echo "$LAST_BETA" | sed 's/v\([0-9]*\.[0-9]*\.[0-9]*\)-.*/\1/')
            RC_BASE="none"
            if [ "$LAST_RC" != "none" ]; then
                RC_BASE=$(echo "$LAST_RC" | sed 's/v\([0-9]*\.[0-9]*\.[0-9]*\)-.*/\1/')
            fi
            
            if [ "$BETA_BASE" != "$RC_BASE" ]; then
                echo "Promoting beta $LAST_BETA to RC..."
                make release-patch-rc
            else
                echo "RC already exists for version $BETA_BASE, skipping"
            fi
        else
            echo "No beta releases found, skipping RC creation"
        fi
        ;;
        
    *)
        echo "ERROR: Unknown release type '$RELEASE_TYPE'"
        echo "Usage: $0 [alpha|beta|rc]"
        exit 1
        ;;
esac

echo "Conditional release check complete"
