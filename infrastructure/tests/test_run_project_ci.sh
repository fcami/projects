#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# Tests for ci/run-project-ci.sh.

test_passing_project() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    add_project "$sb" ok
    out="$("${sb}/infrastructure/ci/run-project-ci.sh" ok)"
    assert_contains "$out" "PASSED: ok"
}

test_failing_target_stops_the_run() {
    local out rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    add_project "$sb" bad 'lint:\n\t@true\nbuild:\n\t@false\ntest:\n\t@echo TEST-RAN\n'
    out="$("${sb}/infrastructure/ci/run-project-ci.sh" bad 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "FAILED: bad — make build"
    case "$out" in *TEST-RAN*) fail "test ran after build failed" ;; esac
}

test_missing_project_fails() {
    local out rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$("${sb}/infrastructure/ci/run-project-ci.sh" nope 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "project directory not found"
}

# "infrastructure" resolves to infrastructure/, not projects/. The
# sandbox gets a stub Makefile so this doesn't run the suite recursively.
test_infrastructure_resolves_to_its_directory() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    printf 'lint:\n\t@echo INFRA-LINT\nbuild:\n\t@true\ntest:\n\t@true\n' \
        > "${sb}/infrastructure/Makefile"
    out="$("${sb}/infrastructure/ci/run-project-ci.sh" infrastructure)"
    assert_contains "$out" "INFRA-LINT"
    assert_contains "$out" "PASSED: infrastructure"
}
