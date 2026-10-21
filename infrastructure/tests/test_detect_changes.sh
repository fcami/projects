#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# Tests for ci/detect-changes.sh, in a throwaway git repository.

# repo_with_projects: sandbox with projects a and b, committed; print path
repo_with_projects() {
    local sb
    sb="$(make_sandbox)"
    add_project "$sb" a
    add_project "$sb" b
    git_in "$sb" init -q
    git_in "$sb" add -A
    git_in "$sb" commit -q -m initial
    echo "$sb"
}

# change <sandbox> <path>: modify (or create) a file and commit it
change() {
    mkdir -p "$(dirname "${1}/${2}")"
    echo "change" >> "${1}/${2}"
    git_in "$1" add -A
    git_in "$1" commit -q -m "change $2"
}

detect() {
    "${1}/infrastructure/ci/detect-changes.sh" "${@:2}"
}

test_first_commit_affects_everything() {
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    assert_eq "$(detect "$sb")" '["a","b"]'
    assert_eq "$(detect "$sb" --infrastructure)" true
}

test_subproject_change_affects_only_it() {
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    change "$sb" projects/a/src.txt
    assert_eq "$(detect "$sb")" '["a"]'
    assert_eq "$(detect "$sb" --infrastructure)" false
}

test_infrastructure_change_affects_everything() {
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    change "$sb" infrastructure/ci/new.sh
    assert_eq "$(detect "$sb")" '["a","b"]'
    assert_eq "$(detect "$sb" --infrastructure)" true
}

test_root_wrapper_counts_as_infrastructure() {
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    change "$sb" new-project.py
    assert_eq "$(detect "$sb" --infrastructure)" true
}

test_readme_change_affects_nothing() {
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    change "$sb" README.md
    assert_eq "$(detect "$sb")" '[]'
    assert_eq "$(detect "$sb" --infrastructure)" false
}

test_explicit_base_ref() {
    local base
    sb="$(repo_with_projects)"
    trap 'rm -rf "$sb"' EXIT
    base="$(git_in "$sb" rev-parse HEAD)"
    change "$sb" projects/a/one.txt
    change "$sb" projects/b/two.txt
    assert_eq "$(detect "$sb" "$base")" '["a","b"]'
    assert_eq "$(detect "$sb" --infrastructure "$base")" false
}
