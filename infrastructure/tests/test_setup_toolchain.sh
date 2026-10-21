#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# Tests for ci/setup-toolchain.sh. Only language "other" is used, and no
# system_packages, so nothing is installed.

# run_setup <sandbox> <project> <ci.yaml content>: print the script output
run_setup() {
    local dir
    if [ "$2" = infrastructure ]; then
        dir="${1}/infrastructure"
    else
        dir="${1}/projects/${2}"
        mkdir -p "$dir"
    fi
    printf '%b' "$3" > "${dir}/ci.yaml"
    "${1}/infrastructure/ci/setup-toolchain.sh" "$2"
}

test_inline_comments_are_stripped() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(run_setup "$sb" demo 'language: other  # rust | python\nversion: stable  # a comment\n')"
    assert_contains "$out" "Language: other"$'\n'
    assert_contains "$out" "Version: stable"$'\n'
}

test_quotes_and_trailing_space_are_stripped() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(run_setup "$sb" demo 'language: "other"   \nversion: "1.0"\n')"
    assert_contains "$out" "Language: other"$'\n'
    assert_contains "$out" "Version: 1.0"$'\n'
}

test_hash_without_space_is_kept() {
    local out rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(run_setup "$sb" demo 'language: c#\n' 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "Unknown language: c#"
}

test_unknown_language_fails() {
    local out rc=0
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(run_setup "$sb" demo 'language: cobol\n' 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "Unknown language: cobol"
}

test_missing_ci_yaml_is_skipped() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    mkdir -p "${sb}/projects/demo"
    out="$("${sb}/infrastructure/ci/setup-toolchain.sh" demo 2>&1)"
    assert_contains "$out" "not found, skipping"
}

test_infrastructure_reads_its_own_ci_yaml() {
    local out
    sb="$(make_sandbox)"
    trap 'rm -rf "$sb"' EXIT
    out="$(run_setup "$sb" infrastructure 'language: other  # tooling\n')"
    assert_contains "$out" "Language: other"$'\n'
}
