#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# lib.sh — Helpers shared by the CI scripts. Source it; don't run it.

# project_dir <repo-root> <project-name>
#
# Print the directory holding a project's Makefile and ci.yaml.
# "infrastructure" is the monorepo tooling itself (infrastructure/);
# any other name is a subproject under projects/.
project_dir() {
    if [ "$2" = "infrastructure" ]; then
        echo "${1}/infrastructure"
    else
        echo "${1}/projects/${2}"
    fi
}
