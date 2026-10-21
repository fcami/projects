# SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net>
# SPDX-License-Identifier: MIT
# infrastructure — Uniform Contract Makefile for the monorepo tooling
#
# The same contract as projects/*/Makefile, applied to infrastructure/
# itself: the CI scripts, new-project.py and the new-project template.
# CI runs it (run-project-ci.sh infrastructure) whenever the
# infrastructure changes, before any subproject.

SHELL_SCRIPTS := $(wildcard ci/*.sh tests/*.sh)
PY_SCRIPTS := new-project.py ../new-project.py

.PHONY: build test lint fmt-check fmt clean

# Syntax-check every script (nothing to compile)
build:
	@for f in $(SHELL_SCRIPTS); do bash -n "$$f" || exit 1; done
	python3 -c 'import ast, sys; [ast.parse(open(f).read(), f) for f in sys.argv[1:]]' $(PY_SCRIPTS)

# Run all tests (each in a throwaway copy of the repo; no network, no sudo)
test:
	bash tests/run.sh

# Static analysis. flake8 is limited to errors (syntax, pyflakes): the
# Python scripts are not written to a style guide.
lint:
	shellcheck -x $(SHELL_SCRIPTS)
	flake8 --select=E9,F $(PY_SCRIPTS)

# No formatter is enforced for shell or Python here
fmt-check:
	@echo "[infrastructure] no formatter configured"

fmt:
	@echo "[infrastructure] no formatter configured"

# Tests clean up after themselves; nothing is built
clean:
	@echo "[infrastructure] nothing to clean"
