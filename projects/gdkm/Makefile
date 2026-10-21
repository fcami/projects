# gdkm — Uniform Contract Makefile
#
# This Makefile implements the monorepo contract. Each target delegates
# to the project's native tooling: the stdlib, black, flake8 and pylint,
# all from distribution packages (no PyPI).
#
# The contract targets are the stable interface between this subproject
# and the CI pipeline. CI calls these targets; it never calls python,
# black, flake8, etc. directly (Martin: Dependency Inversion Principle).

PYTHON ?= python3
export PYTHONPATH := src

# Release version, single source of truth: the Version: tag of gdkm.spec
VERSION := $(shell sed -n 's/^Version:[[:space:]]*//p' gdkm.spec)

.PHONY: build test lint fmt-check fmt clean release

# Compile / prepare (byte-compile only; nothing to install)
build:
	$(PYTHON) -m py_compile src/gdkm.py tests/*.py

# Run all tests
test:
	$(PYTHON) -m unittest discover -s tests -t .

# Static analysis, linting (CI runs lint but not fmt-check, so include it)
lint: fmt-check
	flake8 src tests
	$(PYTHON) -m pylint src/gdkm.py tests

# Verify formatting (no mutation)
fmt-check:
	black --check src tests

# Apply formatting
fmt:
	black src tests

# Remove build artifacts
clean:
	find . -name __pycache__ -prune -exec rm -rf {} +
	rm -f gdkm-*.tar.gz

# Source tarball for gdkm.spec, from committed content only (not the working tree)
release:
	git archive --prefix=gdkm-$(VERSION)/ -o gdkm-$(VERSION).tar.gz HEAD
