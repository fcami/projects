#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# run.sh — Run every test_* function in tests/test_*.sh.
#
# Each test runs in its own `bash -e` process: the first failing command
# or assertion ends that test only. Exit code is non-zero if any failed.
#
# Usage: infrastructure/tests/run.sh

set -uo pipefail

TESTS_DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="${TESTS_DIR}/lib.sh"

# CI variables would change detect-changes.sh's choice of base commit
unset GITHUB_BASE_REF SYSTEM_PULLREQUEST_TARGETBRANCH

passed=0
failed=0
for file in "${TESTS_DIR}"/test_*.sh; do
    tests=$(bash -c '. "$1"; declare -F' _ "$file" | awk '$3 ~ /^test_/ {print $3}')
    for test in $tests; do
        if bash -euo pipefail -c '. "$1"; . "$2"; "$3"' _ "$LIB" "$file" "$test"; then
            echo "ok   ${test}"
            passed=$((passed + 1))
        else
            echo "FAIL ${test}"
            failed=$((failed + 1))
        fi
    done
done

echo ""
echo "${passed} passed, ${failed} failed"
[ "$failed" -gt 0 ] && exit 1
[ "$passed" -gt 0 ] || { echo "no tests found" >&2; exit 1; }
