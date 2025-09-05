#!/bin/bash
# dev-tools/unified/release_orchestrator.sh
# Unified release orchestrator - smart dispatcher for all release types
set -e

MODE=${RELEASE_MODE:-forward}
COMMIT=${RELEASE_COMMIT:-}
VERSION=${RELEASE_VERSION:-}

echo "=== UNIFIED RELEASE ORCHESTRATOR ==="
echo "Mode: $MODE"
echo "Commit: ${COMMIT:-N/A}"
echo "Version: ${VERSION:-N/A}"
echo

case $MODE in
    forward)
        echo "=== FORWARD RELEASE MODE ==="
        echo "Running standard build process for semantic-release..."
        make clean build
        ;;
    historical)
        echo "=== HISTORICAL RELEASE MODE ==="
        if [ -z "$COMMIT" ] || [ -z "$VERSION" ]; then
            echo "ERROR: COMMIT and VERSION required for historical releases"
            echo "Usage: RELEASE_MODE=historical RELEASE_COMMIT=abc123 RELEASE_VERSION=0.0.5"
            exit 1
        fi
        echo "Building historical release $VERSION from commit $COMMIT"
        ./dev-tools/release/build_historical.sh "$COMMIT" "$VERSION"
        ./dev-tools/release/release_backfill.sh "$VERSION" "$COMMIT"
        ;;
    analysis)
        echo "=== ANALYSIS MODE ==="
        echo "Running RC readiness analysis..."
        ./dev-tools/release/analyze_rc_readiness.sh
        ./dev-tools/release/generate_rc_analysis.sh
        ;;
    *)
        echo "ERROR: Unknown mode: $MODE"
        echo "Valid modes: forward, historical, analysis"
        echo
        echo "Examples:"
        echo "  RELEASE_MODE=forward ./release_orchestrator.sh"
        echo "  RELEASE_MODE=historical RELEASE_COMMIT=abc123 RELEASE_VERSION=0.0.5 ./release_orchestrator.sh"
        echo "  RELEASE_MODE=analysis ./release_orchestrator.sh"
        exit 1
        ;;
esac

echo "=== ORCHESTRATOR COMPLETE ==="
