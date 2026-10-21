#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# Tests for new-project.py, and for the template working end to end with
# the CI scripts.

new_project() {
    local sb="$1"
    shift
    python3 "${sb}/infrastructure/new-project.py" "$@" \
        --license MIT --author "Test <test@example.invalid>"
}

test_scaffold_is_complete() {
    local p
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    new_project "$sb" demo --language other > /dev/null
    p="${sb}/projects/demo"
    for f in Makefile ci.yaml README.md CLAUDE.md LICENSE REUSE.toml \
        LICENSES/MIT.txt src tests; do
        assert_file "${p}/${f}"
    done
    if grep -rl '{{PROJECT_NAME}}' "$p"; then
        fail "placeholder left in the files above"
    fi
    assert_contains "$(cat "${p}/LICENSE")" "Test <test@example.invalid>"
    assert_contains "$(cat "${p}/ci.yaml")" "language: other"
}

# Regression: the template's inline comments broke toolchain setup for
# every new subproject ("Unknown language: python  # rust | ...").
test_template_ci_yaml_is_parsed() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    new_project "$sb" demo --language other > /dev/null
    out="$("${sb}/infrastructure/ci/setup-toolchain.sh" demo)"
    assert_contains "$out" "Language: other"$'\n'
    assert_contains "$out" "Version: stable"$'\n'
}

test_existing_project_is_refused() {
    local rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    new_project "$sb" demo > /dev/null
    new_project "$sb" demo > /dev/null 2>&1 || rc=$?
    assert_eq "$rc" 1 "exit code"
}

test_reserved_name_is_refused() {
    local out rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(new_project "$sb" infrastructure 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "reserved"
    [ ! -e "${sb}/projects/infrastructure" ] || fail "directory was created"
}
