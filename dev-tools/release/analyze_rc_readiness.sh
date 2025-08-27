#!/bin/bash
set -e

# RC Readiness Analysis Script
# Determines if current beta is ready for RC promotion

# Get to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

echo "Analyzing RC readiness..."

# Get latest beta tag
LATEST_BETA=$(git tag -l "*-beta*" --sort=-version:refname | head -1)

if [ -z "$LATEST_BETA" ]; then
    echo "No beta releases found, not ready for RC"
    exit 1
fi

echo "Latest beta: $LATEST_BETA"

# Calculate days since latest beta
BETA_DATE=$(git log -1 --format="%ct" "$LATEST_BETA")
CURRENT_DATE=$(date +%s)
DAYS_SINCE_BETA=$(( (CURRENT_DATE - BETA_DATE) / 86400 ))

echo "Days since latest beta: $DAYS_SINCE_BETA"

# Count commits since latest beta
COMMITS_SINCE_BETA=$(git rev-list --count "$LATEST_BETA"..HEAD)
echo "Commits since latest beta: $COMMITS_SINCE_BETA"

# Get test coverage (if available)
TEST_COVERAGE="unknown"
if make test-coverage >/dev/null 2>&1; then
    TEST_COVERAGE=$(make test-coverage 2>/dev/null | grep -E "TOTAL.*%" | tail -1 | awk '{print $NF}' | sed 's/%//' || echo "unknown")
fi
echo "Test coverage: $TEST_COVERAGE%"

# RC readiness criteria
MIN_DAYS=14
MIN_COMMITS=10
MIN_COVERAGE=85

echo ""
echo "RC Readiness Criteria:"
echo "  Days since beta: $DAYS_SINCE_BETA >= $MIN_DAYS"
echo "  Commits accumulated: $COMMITS_SINCE_BETA >= $MIN_COMMITS"
echo "  Test coverage: $TEST_COVERAGE% >= $MIN_COVERAGE%"

# Check if ready for RC
READY=true

if [ "$DAYS_SINCE_BETA" -lt "$MIN_DAYS" ]; then
    echo "FAIL: Insufficient time since beta (need $MIN_DAYS days)"
    READY=false
fi

if [ "$COMMITS_SINCE_BETA" -lt "$MIN_COMMITS" ]; then
    echo "FAIL: Insufficient commits since beta (need $MIN_COMMITS commits)"
    READY=false
fi

if [ "$TEST_COVERAGE" != "unknown" ] && [ "$TEST_COVERAGE" -lt "$MIN_COVERAGE" ]; then
    echo "FAIL: Test coverage below threshold (need $MIN_COVERAGE%)"
    READY=false
fi

if [ "$READY" = "true" ]; then
    echo ""
    echo "PASS: Beta is ready for RC promotion"
    exit 0
else
    echo ""
    echo "WAIT: Beta is not ready for RC yet"
    exit 1
fi
