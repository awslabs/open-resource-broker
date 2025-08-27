#!/bin/bash
set -e

# Generate RC analysis report for GitHub issue

# Get to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

# Get current version info
CURRENT_VERSION=$(yq '.project.version' .project.yml)
NEXT_RC_VERSION=$(echo "$CURRENT_VERSION" | sed 's/-beta\.[0-9]*/-rc.1/')

# Get latest beta info
LATEST_BETA=$(git tag -l "*-beta*" --sort=-version:refname | head -1)
BETA_DATE=$(git log -1 --format="%ct" "$LATEST_BETA")
DAYS_SINCE_BETA=$(( ($(date +%s) - BETA_DATE) / 86400 ))
COMMITS_SINCE_BETA=$(git rev-list --count "$LATEST_BETA"..HEAD)

# Generate report
cat << EOF
## RC Promotion Analysis

**Proposed Version:** \`$NEXT_RC_VERSION\`
**Current Version:** \`$CURRENT_VERSION\`

### Analysis Results

| Metric | Value | Status |
|--------|-------|--------|
| Days since beta | $DAYS_SINCE_BETA | $([ $DAYS_SINCE_BETA -ge 14 ] && echo "PASS" || echo "WAIT") |
| Commits since beta | $COMMITS_SINCE_BETA | $([ $COMMITS_SINCE_BETA -ge 10 ] && echo "PASS" || echo "WAIT") |
| Latest beta | $LATEST_BETA | - |

### Recent Changes

\`\`\`
$(git log --oneline "$LATEST_BETA"..HEAD | head -10)
\`\`\`

### Actions

- **Approve RC:** Comment \`/approve-rc\` to create the release candidate
- **Decline RC:** Comment \`/decline-rc\` to wait for next analysis cycle

### Automation

This suggestion was generated automatically based on beta stability analysis.
Next suggestion will occur after additional commits or time threshold is met.
EOF
