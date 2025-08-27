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
        commits=$(git rev-list --reverse "$from_commit..$to_commit")
        commit_count=$(git rev-list --count "$from_commit..$to_commit")
        
        if [ -n "$commits" ]; then
            if [ "$commit_count" -le 5 ]; then
                # Few commits: show full details without author/date
                while IFS= read -r commit_hash; do
                    if [ -n "$commit_hash" ]; then
                        # Get full commit message and details
                        commit_title=$(git log -1 --format="%s" "$commit_hash")
                        commit_body=$(git log -1 --format="%b" "$commit_hash")
                        
                        echo "### $commit_title"
                        echo ""
                        echo "**Commit:** [\`${commit_hash:0:8}\`](https://github.com/awslabs/open-hostfactory-plugin/commit/$commit_hash)"
                        echo ""
                        
                        if [ -n "$commit_body" ]; then
                            echo "$commit_body"
                            echo ""
                        fi
                    fi
                done <<< "$commits"
            else
                # Many commits: use PR-based summary
                echo "### Summary"
                echo ""
                echo "This release includes **$commit_count commits** with the following changes:"
                echo ""
                
                # Try to get PRs merged in this range
                prs=$(gh pr list --state merged --base main --json number,title,mergedAt --jq '.[] | select(.mergedAt >= "'$(git log -1 --format="%aI" "$from_commit")'" and .mergedAt <= "'$(git log -1 --format="%aI" "$to_commit")'") | "* " + .title + " (#" + (.number | tostring) + ")"' 2>/dev/null || echo "")
                
                if [ -n "$prs" ]; then
                    echo "#### Pull Requests"
                    echo ""
                    echo "$prs"
                    echo ""
                else
                    # Fallback: show commit titles only
                    echo "#### Key Changes"
                    echo ""
                    while IFS= read -r commit_hash; do
                        if [ -n "$commit_hash" ]; then
                            commit_title=$(git log -1 --format="%s" "$commit_hash")
                            echo "* $commit_title ([\`${commit_hash:0:8}\`](https://github.com/awslabs/open-hostfactory-plugin/commit/$commit_hash))"
                        fi
                    done <<< "$commits" | head -20
                    
                    if [ "$commit_count" -gt 20 ]; then
                        echo "* ... and $((commit_count - 20)) more commits"
                    fi
                    echo ""
                fi
            fi
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
    
    # Check if this is truly the first release (from first commit)
    first_commit=$(git rev-list --max-parents=0 HEAD)
    if [ "$from_commit" = "$first_commit" ]; then
        echo "## Initial Release"
        echo ""
        
        # Get the initial commit details
        commit_title=$(git log -1 --format="%s" "$to_commit")
        commit_body=$(git log -1 --format="%b" "$to_commit")
        
        if [ -n "$commit_body" ]; then
            echo "$commit_body"
            echo ""
        else
            echo "First public release of the Open Host Factory Plugin."
            echo ""
        fi
        
        echo "### Features"
        echo "- Cloud provider integration for IBM Spectrum Symphony Host Factory"
        echo "- AWS support with multiple provisioning strategies"
        echo "- REST API with OpenAPI documentation"
        echo "- Clean architecture with dependency injection"
        echo "- Comprehensive testing and CI/CD pipeline"
    else
        echo "## What's Changed"
        echo ""
        
        # Get commit messages in the range
        git log --oneline --no-merges "$from_commit..$to_commit" | while read -r line; do
            echo "- $line"
        done
    fi
    
    echo ""
    local repo_info
    repo_info=$(gh repo view --json owner,name --jq '.owner.login + "/" + .name' 2>/dev/null || echo "awslabs/open-hostfactory-plugin")
    echo "**Full Changelog**: https://github.com/$repo_info/compare/${from_commit:0:8}...${to_commit:0:8}"
}

# Generate and output the notes
generate_notes "$FROM_COMMIT" "$TO_COMMIT"
