#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# Tests for ci/make-release.sh, in a throwaway git repository.

# release_repo: a sandbox monorepo with one subproject "a" under its own
# license (GPL-3.0-only), committed and tagged v1.2.3; print its path
release_repo() {
    local sb
    sb="$(make_sandbox)"
    touch "${sb}/projects/.gitkeep"
    cat > "${sb}/README.md" <<'README'
# Projects

## Subprojects

<!-- subprojects:start -->
| [a](projects/a/) | Python | GPL-3.0-only | demo |
<!-- subprojects:end -->

## Quick Start
README
    printf 'version = 1\n[[annotations]]\npath = "LICENSE"\nSPDX-License-Identifier = "MIT"\n' \
        > "${sb}/REUSE.toml"
    add_project "$sb" a
    printf 'version = 1\n[[annotations]]\npath = "**"\nSPDX-License-Identifier = "GPL-3.0-only"\n' \
        > "${sb}/projects/a/REUSE.toml"
    echo "GPL text" > "${sb}/LICENSES/GPL-3.0-only.txt"
    git_in "$sb" init -q
    git_in "$sb" add -A
    git_in "$sb" commit -q -m initial
    git_in "$sb" tag v1.2.3
    echo "$sb"
}

# unpack <tarball> <dir>: extract and print the top-level entries
unpack() {
    mkdir -p "$2"
    tar -xzf "$1" -C "$2"
    ls -A "$2"
}

test_release_is_clean() {
    local tarball top tree
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    tarball="$("${sb}/infrastructure/ci/make-release.sh")"
    assert_eq "$tarball" "${sb}/dist/projects-v1.2.3.tar.gz" "tarball path"
    top="$(unpack "$tarball" "${sb}/out")"
    assert_eq "$top" "projects-v1.2.3" "top directory"
    tree="${sb}/out/projects-v1.2.3"
    assert_file "${tree}/infrastructure/ci/make-release.sh"
    assert_file "${tree}/projects/.gitkeep"
    assert_eq "$(ls -A "${tree}/projects")" ".gitkeep" "projects/ content"
    [ ! -e "${tree}/.git" ] || fail "git metadata in the tarball"
    assert_file "${tree}/LICENSES/MIT.txt"
    [ ! -e "${tree}/LICENSES/GPL-3.0-only.txt" ] || fail "subproject-only license kept"
    assert_contains "$(cat "${tree}/README.md")" "No subprojects yet"
    case "$(cat "${tree}/README.md")" in
        *"projects/a/"*) fail "subproject still listed in README" ;;
    esac
    assert_contains "$(cat "${tree}/README.md")" "<!-- subprojects:end -->"
}

test_clone_is_left_untouched() {
    local before after
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    before="$(git_in "$sb" status --porcelain --ignored; find "$sb" -path "${sb}/.git" -prune -o -print | sort)"
    "${sb}/infrastructure/ci/make-release.sh" > /dev/null
    rm -rf "${sb}/dist"
    after="$(git_in "$sb" status --porcelain --ignored; find "$sb" -path "${sb}/.git" -prune -o -print | sort)"
    assert_eq "$after" "$before" "clone content"
    assert_file "${sb}/projects/a/Makefile"
}

test_release_can_start_a_new_monorepo() {
    local tarball tree
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    tarball="$("${sb}/infrastructure/ci/make-release.sh" 9.9 "${sb}/rel")"
    assert_eq "$tarball" "${sb}/rel/projects-9.9.tar.gz" "tarball path"
    unpack "$tarball" "${sb}/out" > /dev/null
    tree="${sb}/out/projects-9.9"
    python3 "${tree}/infrastructure/new-project.py" fresh --language other \
        --license MIT --author "Test <test@example.invalid>" > /dev/null
    assert_file "${tree}/projects/fresh/Makefile"
}

test_release_is_reproducible() {
    local one two
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    one="$(sha256sum < "$("${sb}/infrastructure/ci/make-release.sh")")"
    sleep 1
    two="$(sha256sum < "$("${sb}/infrastructure/ci/make-release.sh")")"
    assert_eq "$two" "$one" "tarball checksum"
}

test_uncommitted_changes_are_excluded() {
    local tarball err
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    echo "draft" > "${sb}/DRAFT.md"
    err="$("${sb}/infrastructure/ci/make-release.sh" 2>&1 > /dev/null)"
    assert_contains "$err" "uncommitted changes are not included"
    tarball="${sb}/dist/projects-v1.2.3.tar.gz"
    if tar -tzf "$tarball" | grep -q DRAFT.md; then
        fail "uncommitted file in the tarball"
    fi
}

test_missing_readme_markers_fail() {
    local rc=0 out
    sb="$(release_repo)"
    trap 'rm -rf "$sb"' EXIT
    sed -i '/subprojects:end/d' "${sb}/README.md"
    git_in "$sb" commit -q -am "drop marker"
    out="$("${sb}/infrastructure/ci/make-release.sh" 2>&1)" || rc=$?
    assert_eq "$rc" 1 "exit code"
    assert_contains "$out" "lacks the"
}
