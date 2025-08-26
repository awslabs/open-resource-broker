#!/bin/bash
set -e

# Release notes generator
# Usage: release_notes.sh <from_commit> <to_commit>

if [ $# -ne 2 ]; then
    echo "Usage: $0 <from_commit> <to_commit>"
    exit 1
fi

FROM_COMMIT=$1
TO_COMMIT=$2

# Get to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT"

generate_notes() {
    local from_commit=$1
    local to_commit=$2
    local version=$(make -s get-version)
    
    # Check if this is the first release
    first_commit=$(git rev-list --max-parents=0 HEAD)
    if [ "$from_commit" = "$first_commit" ] && [ -z "$(git tag -l "v*")" ]; then
        echo "## 🎉 Initial Release"
        echo ""
        echo "First public release of the Open Host Factory Plugin."
        echo ""
        echo "### Features"
        echo "- Cloud provider integration for IBM Spectrum Symphony Host Factory"
        echo "- AWS support with multiple provisioning strategies"
        echo "- REST API with OpenAPI documentation"
        echo "- Clean architecture with dependency injection"
        echo "- Comprehensive testing and CI/CD pipeline"
        return 0
    fi
    
    # Try to use GitHub's generate-notes API
    if command -v gh >/dev/null 2>&1; then
        # Find previous tag for comparison
        previous_tag=""
        if [ "$from_commit" != "$first_commit" ]; then
            # Find the tag that points to from_commit or is closest before it
            previous_tag=$(git tag -l "v*" --sort=-version:refname --merged "$from_commit" | head -1)
        fi
        
        if [ -n "$previous_tag" ]; then
            echo "Generating notes from $previous_tag to v$version..."
            gh api repos/$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')/releases/generate-notes \
                --field tag_name="v$version" \
                --field previous_tag_name="$previous_tag" \
                --jq '.body' 2>/dev/null || generate_fallback_notes "$from_commit" "$to_commit"
        else
            generate_fallback_notes "$from_commit" "$to_commit"
        fi
    else
        generate_fallback_notes "$from_commit" "$to_commit"
    fi
}

generate_fallback_notes() {
    local from_commit=$1
    local to_commit=$2
    
    echo "## What's Changed"
    echo ""
    
    # Get commit messages in the range
    git log --oneline --no-merges "$from_commit..$to_commit" | while read -r line; do
        echo "- $line"
    done
    
    echo ""
    echo "**Full Changelog**: https://github.com/$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')/compare/${from_commit:0:8}...${to_commit:0:8}"
}

# Generate and output the notes
generate_notes "$FROM_COMMIT" "$TO_COMMIT"
