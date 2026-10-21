#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# setup-toolchain.sh — Install the toolchain for a subproject.
#
# Reads projects/$PROJECT/ci.yaml (infrastructure/ci.yaml for the
# project named "infrastructure") to determine language, version,
# and any extra system packages or setup commands.
#
# Usage: infrastructure/ci/setup-toolchain.sh <project-name>

set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <project-name>" >&2
    exit 1
fi

PROJECT="$1"
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck source=SCRIPTDIR/lib.sh
. "$(dirname "$0")/lib.sh"
CI_YAML="$(project_dir "$REPO_ROOT" "$PROJECT")/ci.yaml"

if [ ! -f "$CI_YAML" ]; then
    echo "Warning: ${CI_YAML} not found, skipping toolchain setup" >&2
    exit 0
fi

# Parse ci.yaml (portable: grep + sed, no yq dependency).
# Inline comments ("language: rust  # ...", as in the template) are
# stripped; as in YAML, a comment starts with whitespace followed by '#'.
parse_yaml_field() {
    grep "^${1}:" "$CI_YAML" 2>/dev/null \
        | sed -e "s/^${1}:[[:space:]]*//" -e 's/[[:space:]]\{1,\}#.*$//' -e 's/[[:space:]]*$//' \
        | tr -d '"' || true
}

LANGUAGE=$(parse_yaml_field "language")
VERSION=$(parse_yaml_field "version")
SYSTEM_PACKAGES=$(parse_yaml_field "system_packages")

echo "=== Setting up toolchain for ${PROJECT} ==="
echo "Language: ${LANGUAGE:-not specified}"
echo "Version: ${VERSION:-not specified}"

# Install system packages if specified
if [ -n "$SYSTEM_PACKAGES" ]; then
    echo "Installing system packages: ${SYSTEM_PACKAGES}"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update -qq
        # shellcheck disable=SC2086
        sudo apt-get install -y -qq $SYSTEM_PACKAGES
    elif command -v dnf >/dev/null 2>&1; then
        # shellcheck disable=SC2086
        sudo dnf install -y -q $SYSTEM_PACKAGES
    else
        echo "Warning: no supported package manager found" >&2
    fi
fi

# Install language-specific toolchain
case "${LANGUAGE}" in
    rust)
        if ! command -v rustup >/dev/null 2>&1; then
            curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --default-toolchain "${VERSION:-stable}"
            # shellcheck disable=SC1091
            source "$HOME/.cargo/env"
        else
            rustup toolchain install "${VERSION:-stable}"
            rustup default "${VERSION:-stable}"
        fi
        ;;
    python)
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get install -y -qq "python${VERSION:-3}" "python${VERSION:-3}-pip" "python${VERSION:-3}-venv"
        fi
        ;;
    c|cpp)
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get install -y -qq build-essential cmake
        elif command -v dnf >/dev/null 2>&1; then
            sudo dnf install -y -q gcc gcc-c++ cmake make
        fi
        ;;
    go)
        if ! command -v go >/dev/null 2>&1; then
            GO_VERSION="${VERSION:-1.22.0}"
            curl -sSfL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" | sudo tar -C /usr/local -xz
            export PATH="/usr/local/go/bin:$PATH"
        fi
        ;;
    node)
        if ! command -v node >/dev/null 2>&1; then
            curl -fsSL https://deb.nodesource.com/setup_"${VERSION:-20}".x | sudo -E bash -
            sudo apt-get install -y -qq nodejs
        fi
        ;;
    other|"")
        echo "No automatic toolchain setup for language '${LANGUAGE}'"
        ;;
    *)
        echo "Unknown language: ${LANGUAGE}" >&2
        exit 1
        ;;
esac

# Run extra setup commands if specified
SETUP_LINES=$(grep -A 100 "^setup_commands:" "$CI_YAML" 2>/dev/null | tail -n +2 | grep "^  - " | sed 's/^  - //' || true)
if [ -n "$SETUP_LINES" ]; then
    echo "Running setup commands..."
    while IFS= read -r cmd; do
        echo "  $ ${cmd}"
        eval "$cmd"
    done <<< "$SETUP_LINES"
fi

echo "=== Toolchain setup complete for ${PROJECT} ==="
