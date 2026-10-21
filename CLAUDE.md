<!-- SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net> -->
<!-- SPDX-License-Identifier: MIT -->
# Projects Monorepo — Development Rules

Rules for working in this repository. Loaded automatically at the
start of every Claude Code session.

## Repository Structure

This is a monorepo hosting multiple independent subprojects. Each
subproject lives in `projects/<name>/` with its own license, language,
and build system.

```
projects/              Subprojects (one directory per project)
infrastructure/        All monorepo tooling
├── ci/                CI scripts (portable bash)
├── docs/              Design document, user guide, LLM prompts
├── templates/         Scaffold for new subprojects
└── new-project.py     Project creation script
.github/workflows/     GitHub Actions CI
.azure-pipelines/      Azure Pipelines CI
new-project.py         Root wrapper (delegates to infrastructure/)
```

## The Uniform Contract

Every subproject must implement these `Makefile` targets:
`build`, `test`, `lint`, `fmt-check`, `fmt`, `clean`.
Optional: `release`.

CI calls these targets. Never call language-specific tooling
(cargo, pytest, cmake) directly from CI — the Makefile is the
abstraction boundary (Martin: Dependency Inversion Principle).

## Creating a New Subproject

```bash
./new-project.py <name> --language <lang> --license <SPDX-ID>
```

Or use the LLM prompts in `infrastructure/docs/llm-prompts.md`.

**No commit may be made to a subproject before its LICENSE file exists.**

## Licensing

This repo is [REUSE-compliant](https://reuse.software/). Every file
has explicit copyright and license information via SPDX headers or
`REUSE.toml`. Run `reuse lint` to verify.

Infrastructure (`infrastructure/`, `.github/`, `.azure-pipelines/`,
root-level files) is MIT-licensed. Each subproject has its own license
under `projects/<name>/LICENSE`. The REUSE metadata makes this scoping
machine-verifiable — the root MIT cannot apply to subprojects.

See `infrastructure/docs/design.md` "Licensing" for full rules.

## CI Pipeline

- `infrastructure/ci/detect-changes.sh` — determines which subprojects changed
- `infrastructure/ci/setup-toolchain.sh` — installs language toolchain per subproject
- `infrastructure/ci/run-project-ci.sh` — runs lint, build, test for a subproject
- `infrastructure/ci/make-release.sh` — clean monorepo tarball without subprojects
  (`make -C infrastructure release`; on `v*` tags, `.github/workflows/release.yaml`)

Infrastructure changes (`infrastructure/`, root files) trigger ALL
subprojects, after the infrastructure's own contract passes:
`infrastructure/Makefile` (shellcheck, flake8, `infrastructure/tests/`).
Run it locally with `infrastructure/ci/run-project-ci.sh infrastructure`.
Changes to the CI scripts or `new-project.py` need a test there.

The README's subproject list must stay between its `subprojects:start` /
`subprojects:end` markers: the release replaces that span.

## Cross-Cutting Changes

When modifying the contract, CI scripts, or templates: update ALL
affected subprojects atomically. Don't leave the repo in a
half-migrated state (Winters et al.: large-scale changes).

## Design Principles

This monorepo follows principles from Booch, Gamma, Lakos, Beck,
Fowler, Martin, Humble+Farley, and Winters+Manshreck+Wright.
See `infrastructure/docs/design.md` for the full treatment.

Key rules for subprojects:
- One file, one responsibility (Martin: SRP)
- Acyclic dependencies between modules (Lakos, Martin: ADP)
- Tests are first-class artifacts (Beck)
- Test first, change second
- Favor composition over inheritance (Gamma)
- Everything in version control (Humble + Farley)
- The pipeline is the authority on whether a change is safe

## Commits

- Always use: `git commit --signoff`
- Author: set identity via env vars (see global CLAUDE.md)
- One logical change per commit
- Refactoring commits must not change behavior
- Enhancement commits must not restructure code

## References

- `infrastructure/docs/design.md` — monorepo design document
- `infrastructure/docs/user-guide.md` — how to create and manage subprojects
- `infrastructure/docs/llm-prompts.md` — prompts for LLM-assisted work
- `infrastructure/templates/new-project/` — scaffold with all template documents
