#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# detect-changes.sh — Determine which subprojects were affected by a changeset.
#
# Outputs a JSON array of subproject directory names, e.g.: ["project-a","project-c"]
# If infrastructure/ or root config files changed, ALL subprojects are affected.
#
# With --infrastructure, outputs "true" or "false" instead: whether the
# monorepo infrastructure itself changed (CI then runs its own contract).
#
# Usage:
#   infrastructure/ci/detect-changes.sh              # auto-detect: PR base or HEAD~1
#   infrastructure/ci/detect-changes.sh <base_ref>   # explicit base ref
#   infrastructure/ci/detect-changes.sh --infrastructure [<base_ref>]

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

MODE=projects
if [ "${1:-}" = "--infrastructure" ]; then
    MODE=infrastructure
    shift
fi

# Determine the base commit to diff against
if [ $# -ge 1 ]; then
    BASE="$1"
elif [ -n "${GITHUB_BASE_REF:-}" ]; then
    # GitHub Actions pull request
    BASE="origin/${GITHUB_BASE_REF}"
elif [ -n "${SYSTEM_PULLREQUEST_TARGETBRANCH:-}" ]; then
    # Azure Pipelines pull request
    BASE="origin/${SYSTEM_PULLREQUEST_TARGETBRANCH}"
elif git rev-parse HEAD~1 >/dev/null 2>&1; then
    # Push to branch — compare with previous commit
    BASE="HEAD~1"
else
    # First commit — everything is changed
    BASE="--root"
fi

# Get list of changed files
if [ "$BASE" = "--root" ]; then
    CHANGED_FILES=$(git diff-tree --root --no-commit-id --name-only -r HEAD)
else
    CHANGED_FILES=$(git diff --name-only "$BASE"...HEAD 2>/dev/null || git diff --name-only "$BASE" HEAD)
fi

# Check if infrastructure changed (triggers all subprojects)
INFRA_CHANGED=false
while IFS= read -r file; do
    case "$file" in
        infrastructure/*|.github/*|.azure-pipelines/*|CLAUDE.md|LICENSE|REUSE.toml|LICENSES/*|new-project.py)
            INFRA_CHANGED=true
            break
            ;;
    esac
done <<< "$CHANGED_FILES"

if [ "$MODE" = infrastructure ]; then
    echo "$INFRA_CHANGED"
    exit 0
fi

# Collect affected subprojects
declare -A AFFECTED

if [ "$INFRA_CHANGED" = true ]; then
    # All subprojects affected
    for dir in projects/*/; do
        if [ -f "${dir}Makefile" ]; then
            name=$(basename "$dir")
            AFFECTED["$name"]=1
        fi
    done
else
    # Only subprojects with changed files
    while IFS= read -r file; do
        if [[ "$file" == projects/* ]]; then
            # Extract subproject name (first path component after projects/)
            name=$(echo "$file" | cut -d/ -f2)
            if [ -f "projects/${name}/Makefile" ]; then
                AFFECTED["$name"]=1
            fi
        fi
    done <<< "$CHANGED_FILES"
fi

# Output as JSON array
RESULT="["
FIRST=true
for name in $(echo "${!AFFECTED[@]}" | tr ' ' '\n' | sort); do
    if [ "$FIRST" = true ]; then
        FIRST=false
    else
        RESULT+=","
    fi
    RESULT+="\"${name}\""
done
RESULT+="]"

echo "$RESULT"
