<!-- SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net> -->
<!-- SPDX-License-Identifier: MIT -->
# User Guide — Projects Monorepo

How to use this monorepo: create projects, run CI, manage releases.

## Quick Start

### Create a new subproject

```bash
# Using the script (recommended)
./new-project.py my-tool --language rust --license MIT

# Or manually
cp -r infrastructure/templates/new-project projects/my-tool
# Edit files, replace {{PROJECT_NAME}} with my-tool
```

### Work on your project

```bash
cd projects/my-tool
# Edit src/, tests/, Makefile
make build
make test
make lint
```

### Verify before committing

```bash
make -C projects/my-tool lint build test
```

### Commit and push

CI detects which subprojects changed and runs their contract targets
in parallel. You don't need to configure anything — the CI pipeline
picks up new subprojects automatically.

---

## Repository Layout

```
projects/                    # All subprojects live here
├── project-a/               # Each is independent
├── project-b/               # Each has its own license
└── .../
infrastructure/              # All monorepo tooling
├── ci/                      # CI scripts (portable bash)
│   ├── detect-changes.sh    # Which subprojects changed?
│   ├── setup-toolchain.sh   # Install language toolchain
│   └── run-project-ci.sh    # Run contract targets
├── docs/
│   ├── design.md            # Monorepo design document
│   ├── user-guide.md        # This file
│   └── llm-prompts.md       # Prompts for LLM-assisted work
├── templates/
│   └── new-project/         # Scaffold for new subprojects
└── new-project.py           # Project creation script
.github/workflows/
└── ci.yaml                  # GitHub Actions entry point
.azure-pipelines/
└── pipeline.yaml            # Azure Pipelines entry point
new-project.py               # Root wrapper
```

## The Uniform Contract

Every subproject exposes these targets via a `Makefile`:

| Target | Purpose | Required? |
|---|---|---|
| `make build` | Compile / prepare | Yes |
| `make test` | Run all tests | Yes |
| `make lint` | Static analysis, linting | Yes |
| `make fmt-check` | Verify formatting (no mutation) | Yes |
| `make fmt` | Apply formatting | Yes |
| `make clean` | Remove build artifacts | Yes |
| `make release` | Produce release artifact | Optional |

The Makefile is an adapter: it translates these uniform targets into
language-specific commands. CI calls the contract; it never calls
cargo, pytest, cmake, etc. directly.

### Makefile Examples

**Rust:**
```makefile
build:
	cargo build
test:
	cargo test
lint:
	cargo clippy -- -D warnings
```

**Python:**
```makefile
build:
	python -m pip install -e .
test:
	python -m pytest tests/
lint:
	python -m ruff check src/ tests/
```

**C++ (CMake):**
```makefile
build:
	cmake -B build && cmake --build build -j$$(nproc)
test:
	ctest --test-dir build
lint:
	cmake --build build --target clang-tidy
```

See `infrastructure/templates/new-project/Makefile` for complete examples including
Go and Node.

## Creating a New Subproject

### Option 1: Python script (recommended)

```bash
./new-project.py PROJECT_NAME --language LANGUAGE --license LICENSE
```

Arguments:
- `PROJECT_NAME` — directory name under `projects/`
- `--language` — rust, python, c, cpp, go, node, other
- `--license` — SPDX identifier: MIT, Apache-2.0, GPL-3.0-only,
  LGPL-3.0-only, BSD-2-Clause, BSD-3-Clause

The script:
1. Copies the template into `projects/PROJECT_NAME/`
2. Replaces `{{PROJECT_NAME}}` in all files
3. Sets the language in `ci.yaml`
4. Creates `LICENSE` (`--license` is required)
5. Sets up REUSE compliance (`REUSE.toml` + `LICENSES/`)
6. Creates `src/` and `tests/` directories
7. Prints next steps

### Option 2: LLM-assisted

Use the prompts in `infrastructure/docs/llm-prompts.md`. Prompt 1 ("Create a New
Subproject") walks an LLM through the full creation process.

### Option 3: Manual

```bash
cp -r infrastructure/templates/new-project projects/my-tool
cd projects/my-tool
# Replace {{PROJECT_NAME}} with my-tool in all .md files
# Edit Makefile — uncomment the language block for your toolchain
# Edit ci.yaml — set language and version
# Create LICENSE with full license text
# Create LICENSES/<spdx-id>.txt (run: reuse download <spdx-id>)
# Create REUSE.toml covering all files (see existing subprojects for format)
# Create src/ and tests/ directories
```

### After creation

1. **Edit the Makefile.** Uncomment and adapt the block for your
   language. Verify each target works: `make build`, `make test`,
   `make lint`, `make fmt-check`.

2. **License and REUSE.** `--license` is required, so both `LICENSE`
   and REUSE metadata (`REUSE.toml` + `LICENSES/`) are created
   automatically. Verify with `reuse lint` from the repo root.

3. **Write a README.** Describe what the project does, how to build
   it, and how to use it.

4. **Fill in the docs.** Start with GOALS.md (why the project exists)
   and ARCHITECTURE.md (how it's structured). The other template files
   (CodeReview.md, TestPlan.md, etc.) can be filled in as the project
   matures.

5. **Verify the contract.** Run all targets:
   ```bash
   make -C projects/my-tool lint build test
   ```

6. **Commit and push.** CI picks up the new subproject automatically.

## Importing an Existing Project

Use LLM Prompt 2 ("Import an Existing Project") or do it manually:

1. Copy the source into `projects/EXISTING_NAME/`
2. Add a `Makefile` implementing the contract
3. Add a `ci.yaml` declaring the toolchain
4. Ensure a `LICENSE` exists
5. Set up REUSE: create `REUSE.toml` + `LICENSES/<spdx-id>.txt`
6. Copy template docs you want (CLAUDE.md, CodeReview.md, etc.)
7. Verify: `make -C projects/EXISTING_NAME lint build test`
8. Verify: `reuse lint`

Note: git history is not preserved when importing into the monorepo.
Document the original repository URL in the project's README.

## CI Pipeline

### How it works

1. **Detect**: `infrastructure/ci/detect-changes.sh` compares the changeset against
   `projects/*/` and outputs a JSON list of affected subprojects.
2. **Fan-out**: each affected subproject gets a parallel CI job that
   runs `lint → build → test`.
3. **Infrastructure changes** (`infrastructure/`, `.github/`, `.azure-pipelines/`,
   `CLAUDE.md`, `LICENSE`, `REUSE.toml`, `LICENSES/`) trigger ALL subprojects.

### Running CI locally

```bash
# Run CI for a specific subproject
infrastructure/ci/run-project-ci.sh my-tool

# See which subprojects would be affected
infrastructure/ci/detect-changes.sh

# Set up the toolchain for a subproject (usually not needed locally)
infrastructure/ci/setup-toolchain.sh my-tool
```

### Triggers

| Event | What runs |
|---|---|
| Push to `main` | Affected subprojects |
| Pull request | Affected subprojects |
| Tag `projects/foo/v*` | That subproject's `make release` |
| Weekly schedule | ALL subprojects (catches dependency rot) |

## Licensing

This repo is [REUSE-compliant](https://reuse.software/). The root
`LICENSE` (MIT) covers infrastructure only — per-file SPDX metadata
makes the scoping machine-verifiable. Each subproject has its own
`LICENSE` file. Run `reuse lint` to verify compliance. See
`infrastructure/docs/design.md` "Licensing" section for full rules,
including LGPL guidance.

Key rules:
- Independent subprojects have no license interaction
- Cross-project dependencies create license obligations
- Shared libraries should use the most permissive compatible license

## Project Documentation

Each subproject can have these files (all optional except Makefile,
README, and LICENSE):

| File | Purpose |
|---|---|
| `Makefile` | **Required.** Implements the contract |
| `README.md` | **Required.** What, why, how to use |
| `LICENSE` | **Required.** License for this subproject |
| `ci.yaml` | Toolchain declaration for CI |
| `CHANGELOG.md` | User-facing changes per release |
| `CLAUDE.md` | Development rules for LLM assistants |
| `ARCHITECTURE.md` | Module layout, design decisions |
| `CodeReview.md` | Review guidelines and code smell catalog |
| `TODO.md` | Current work, technical debt |
| `ROADMAP.md` | Future phases and plans |
| `GOALS.md` | What the project does and why |
| `USER_STORIES.md` | Requirements and acceptance criteria |
| `TestPlan.md` | Test plans and smoke tests |
| `ADR.md` | Architecture Decision Record |
| `DEVELOPER_GUIDE.md` | Build, test, contribute guide |
| `ReleaseCriteria.md` | Release checklist |

Templates for all of these are in `infrastructure/templates/new-project/`. They
include guidance from Booch, Gamma, Lakos, Beck, Fowler, Martin,
Humble+Farley, and Winters et al.

## Working with LLMs

The `infrastructure/docs/llm-prompts.md` file contains ready-to-use prompts for
common tasks:

1. Create a new subproject
2. Import an existing project
3. Add CI for a new language
4. Code review a subproject
5. Pre-release check
6. Cross-cutting change
7. Refactoring under test coverage
8. Architecture review

Each prompt is self-contained — copy it, fill in the placeholders,
and paste it into your LLM session.
