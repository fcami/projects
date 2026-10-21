#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# run-project-ci.sh — Run the CI contract for a single subproject.
#
# Executes lint, build, test in order. Stops on first failure.
# Exit code is 0 if all pass, non-zero on first failure.
#
# Usage: infrastructure/ci/run-project-ci.sh <project-name>
#
# <project-name> is a directory under projects/, or "infrastructure" for
# the monorepo tooling itself.

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <project-name>" >&2
    exit 1
fi

PROJECT="$1"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/lib.sh
. "$(dirname "$0")/lib.sh"
PROJECT_DIR="$(project_dir "$REPO_ROOT" "$PROJECT")"

if [ ! -d "$PROJECT_DIR" ]; then
    echo "Error: project directory not found: ${PROJECT_DIR}" >&2
    exit 1
fi

if [ ! -f "${PROJECT_DIR}/Makefile" ]; then
    echo "Error: no Makefile in ${PROJECT_DIR}" >&2
    exit 1
fi

echo "========================================"
echo "CI: ${PROJECT}"
echo "========================================"

TARGETS=("lint" "build" "test")

for target in "${TARGETS[@]}"; do
    echo ""
    echo "--- ${PROJECT}: make ${target} ---"
    if ! make -C "$PROJECT_DIR" "$target"; then
        echo ""
        echo "FAILED: ${PROJECT} — make ${target}" >&2
        exit 1
    fi
done

echo ""
echo "PASSED: ${PROJECT} — all CI targets succeeded"
