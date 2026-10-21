#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# lib.sh — Test helpers. Sourced by tests/run.sh; not run directly.

INFRA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(dirname "$INFRA_DIR")"

# make_sandbox: create a throwaway monorepo (infrastructure/, LICENSES/,
# empty projects/) and print its path. Tests never touch the real repo.
make_sandbox() {
    local dir
    dir="$(mktemp -d)"
    cp -r "$INFRA_DIR" "${dir}/infrastructure"
    cp -r "${REPO_ROOT}/LICENSES" "${dir}/LICENSES"
    mkdir "${dir}/projects"
    echo "$dir"
}

# git_in <dir> <git args...>: run git with a fixed identity, no user config
git_in() {
    local dir="$1"
    shift
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
        git -C "$dir" -c user.name=Test -c user.email=test@example.invalid \
        -c init.defaultBranch=main -c commit.gpgsign=false "$@"
}

# add_project <sandbox> <name> [<makefile body>]: a minimal subproject
add_project() {
    mkdir -p "${1}/projects/${2}"
    printf '%b' "${3:-lint:\n\t@true\nbuild:\n\t@true\ntest:\n\t@true\n}" \
        > "${1}/projects/${2}/Makefile"
}

fail() {
    echo "    FAIL: $*" >&2
    return 1
}

assert_eq() {
    [ "$1" = "$2" ] || fail "${3:-value}: expected [$2], got [$1]"
}

assert_contains() {
    case "$1" in
        *"$2"*) ;;
        *) fail "${3:-output} does not contain [$2]: $1" ;;
    esac
}

assert_file() {
    [ -e "$1" ] || fail "missing: $1"
}
