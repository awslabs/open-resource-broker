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
    local version
    version=$(make -s get-version)
    
    # Check if this is the first release
    first_commit=$(git rev-list --max-parents=0 HEAD)
    if [ "$from_commit" = "$first_commit" ] && [ -z "$(git tag -l "v*")" ]; then
        echo "## Initial Release"
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
    
    # For backfill releases, generate notes based on actual commit range
    if [ "$from_commit" != "$first_commit" ]; then
        echo "## Changes in this release"
        echo ""
        
        # Get commits in the range (excluding from_commit, including to_commit)
        commits=$(git log --oneline --reverse "$from_commit..$to_commit")
        
        if [ -n "$commits" ]; then
            echo "### Commits"
            echo ""
            while IFS= read -r commit_line; do
                commit_hash=$(echo "$commit_line" | cut -d' ' -f1)
                commit_msg=$(echo "$commit_line" | cut -d' ' -f2-)
                echo "- $commit_msg ([${commit_hash}](https://github.com/awslabs/open-hostfactory-plugin/commit/$commit_hash))"
            done <<< "$commits"
        else
            echo "No new commits in this release."
        fi
        
        echo ""
        echo "**Full Changelog**: https://github.com/awslabs/open-hostfactory-plugin/compare/${from_commit:0:8}...${to_commit:0:8}"
    else
        # First release - use fallback notes
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
    local repo_info
    repo_info=$(gh repo view --json owner,name --jq '.owner.login + "/" + .name' 2>/dev/null || echo "owner/repo")
    echo "**Full Changelog**: https://github.com/$repo_info/compare/${from_commit:0:8}...${to_commit:0:8}"
}

# Generate and output the notes
generate_notes "$FROM_COMMIT" "$TO_COMMIT"
