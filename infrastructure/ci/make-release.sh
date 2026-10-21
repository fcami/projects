#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# make-release.sh — Build a clean tarball of the monorepo infrastructure.
#
# The tarball is the repository as committed at HEAD, without git
# metadata and without any subproject: projects/ keeps only .gitkeep,
# the README's subproject list is reset to its empty placeholder, and
# license texts used only by subprojects are dropped from LICENSES/.
# Unpacked, it is a fresh monorepo ready for `git init`.
#
# Nothing in the clone is modified or deleted: the script reads
# committed content with `git archive`, works in a temporary directory
# and writes only the tarball.
#
# Usage: infrastructure/ci/make-release.sh [<version>] [<output-dir>]
#   <version>     default: `git describe --tags --always` of HEAD
#   <output-dir>  default: dist/ at the repository root
#
# Output: <output-dir>/projects-<version>.tar.gz, top directory
# projects-<version>/. Prints the tarball path.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${1:-$(git -C "$REPO_ROOT" describe --tags --always)}"
OUT_DIR="${2:-${REPO_ROOT}/dist}"
NAME="projects-${VERSION}"

# README markers around the subproject list, and what replaces it
START_MARK='<!-- subprojects:start -->'
END_MARK='<!-- subprojects:end -->'
# The backticks are Markdown, not command substitution
# shellcheck disable=SC2016
PLACEHOLDER='(No subprojects yet. Create one with `./new-project.py`.)'

if [ -n "$(git -C "$REPO_ROOT" status --porcelain)" ]; then
    echo "warning: uncommitted changes are not included (the release is HEAD)" >&2
fi

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
TREE="${STAGE}/${NAME}"

# Committed content only, without the subprojects (projects/.gitkeep stays)
git -C "$REPO_ROOT" archive --prefix="${NAME}/" HEAD -- . \
    ':(exclude,glob)projects/*/**' | tar -x -C "$STAGE"

# Reset the README's subproject list
README="${TREE}/README.md"
if ! grep -qF "$START_MARK" "$README" || ! grep -qF "$END_MARK" "$README"; then
    echo "Error: README.md lacks the ${START_MARK} / ${END_MARK} markers" >&2
    exit 1
fi
awk -v start="$START_MARK" -v end="$END_MARK" -v ph="$PLACEHOLDER" '
    index($0, start) { print; print ""; print ph; print ""; skip = 1; next }
    index($0, end)   { skip = 0 }
    !skip
' "$README" > "${STAGE}/README.md"
mv "${STAGE}/README.md" "$README"

# Drop license texts no remaining file declares (REUSE: no unused licenses).
# A declaration is an SPDX license-identifier header comment (after #, //,
# /*, <!-- or ;) or a REUSE.toml license-identifier key, at the start of a
# line; prose that merely mentions SPDX doesn't count.
DECLARATION='^[[:space:]]*(#|//|/\*|<!--|;)?[[:space:]]*SPDX-License-Identifier[[:space:]]*[:=]'
DECLARED="$(grep -rhE --exclude-dir=LICENSES "$DECLARATION" "$TREE" || true)"
for text in "${TREE}"/LICENSES/*.txt; do
    [ -e "$text" ] || continue
    id="$(basename "$text" .txt)"
    if ! grep -qwF -- "$id" <<< "$DECLARED"; then
        rm "$text"
    fi
done

# Reproducible tarball: fixed order, owner and mtime (the commit date)
MTIME="$(git -C "$REPO_ROOT" log -1 --format=%ct HEAD)"
mkdir -p "$OUT_DIR"
OUT="$(cd "$OUT_DIR" && pwd)/${NAME}.tar.gz"
tar -C "$STAGE" --sort=name --owner=0 --group=0 --numeric-owner \
    --mtime="@${MTIME}" -cf - "$NAME" | gzip -n > "$OUT"

echo "$OUT"
