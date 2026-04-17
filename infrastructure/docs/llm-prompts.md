<!-- SPDX-FileCopyrightText: 2026 François Cami <contribs@fcami.net> -->
<!-- SPDX-License-Identifier: MIT -->
# LLM Prompts for Project Creation and Maintenance

Prompts for use with Claude Code (or any LLM assistant) when working
with this monorepo. Copy-paste the relevant prompt and fill in the
bracketed placeholders.

---

## Prompt 1: Create a New Subproject

Use this when starting a brand new project in the monorepo.

```
I have a monorepo at ~/claude/projects that uses a uniform Makefile
contract (build, test, lint, fmt-check, fmt, clean, release) for all
subprojects. The design is documented in infrastructure/docs/design.md and templates
are in infrastructure/templates/new-project/.

Create a new subproject called [PROJECT_NAME] in [LANGUAGE].
License: [LICENSE, e.g., MIT, Apache-2.0, GPL-3.0-only].

The project will: [ONE SENTENCE DESCRIBING WHAT IT DOES].

Steps:
1. Run ./new-project.py [PROJECT_NAME] --language [LANGUAGE] --license [LICENSE]
2. Edit the Makefile to wire up the [LANGUAGE] build system
3. Write a README.md describing the project
4. Set up the initial source structure in src/
5. Write an initial test in tests/
6. Verify: make -C projects/[PROJECT_NAME] lint build test
7. Verify: reuse lint (REUSE compliance — the script sets this up)
8. Fill in GOALS.md with what the project does and why
9. Fill in ARCHITECTURE.md with the initial module layout

Do not commit until make lint build test passes and reuse lint passes.
```

---

## Prompt 2: Import an Existing Project

Use this when moving an existing standalone project into the monorepo.

```
I have a monorepo at ~/claude/projects with a uniform Makefile contract
(build, test, lint, fmt-check, fmt, clean, release).

Import the existing project at [SOURCE_PATH] as a subproject called
[PROJECT_NAME].

Steps:
1. Copy the source into projects/[PROJECT_NAME]/
2. Copy infrastructure/templates/new-project/Makefile to projects/[PROJECT_NAME]/Makefile
   (don't overwrite existing files)
3. Edit the Makefile to delegate each contract target to the project's
   native build system (e.g., make build -> cargo build)
4. Create a ci.yaml declaring the language and version
5. Ensure a LICENSE file exists in the subproject
6. Set up REUSE compliance: create REUSE.toml + LICENSES/<spdx-id>.txt
   (see existing subprojects for the format, or run reuse download <id>)
7. Copy any missing template files (CLAUDE.md, CodeReview.md, etc.)
   from infrastructure/templates/new-project/ and fill in {{PROJECT_NAME}}
8. Verify: make -C projects/[PROJECT_NAME] lint build test
9. Verify: reuse lint
10. If the project has existing docs, reconcile them with the template
   structure

Preserve the project's git history if possible (note: in a monorepo,
history is typically NOT preserved — document the original repo URL
in the README).
```

---

## Prompt 3: Add CI for a New Language

Use this when adding the first subproject in a language not yet
represented.

```
I have a monorepo at ~/claude/projects. The CI scripts in infrastructure/ci/ handle
toolchain setup for various languages (see infrastructure/ci/setup-toolchain.sh).

I'm adding the first [LANGUAGE] subproject. Update:
1. infrastructure/ci/setup-toolchain.sh — add a case for [LANGUAGE] that installs
   [TOOLCHAIN] version [VERSION]
2. infrastructure/templates/new-project/Makefile — add a commented-out [LANGUAGE]
   block showing the standard targets
3. Verify the setup works: create a test project, run the CI script

Do not modify existing language blocks. The CI scripts must remain
portable (bash, no exotic dependencies).
```

---

## Prompt 4: Code Review a Subproject

Use this to review a subproject against the project's engineering
standards.

```
Review projects/[PROJECT_NAME]/ against the standards in
infrastructure/templates/new-project/CodeReview.md.

Check:
1. Does the Makefile implement all contract targets? Do they work?
2. Does the project have a LICENSE file?
3. Architecture: one file one responsibility, no god files, no cycles
4. Tests: do they exist? Do they pin behavior? Golden files?
5. Code smells: duplication, magic numbers, stringly typed concepts
6. SOLID principles: SRP, OCP, DIP at module boundaries
7. Technical debt: is it tracked in TODO.md? Classified?
8. Documentation: README, ARCHITECTURE, CHANGELOG up to date?

Output: a review entry in the format from CodeReview.md (date, commit,
findings, proposed actions).
```

---

## Prompt 5: Pre-Release Check

Use this before tagging a release for a subproject.

```
Run the release criteria checklist from
infrastructure/templates/new-project/ReleaseCriteria.md against
projects/[PROJECT_NAME]/.

For each item:
- Check whether it passes
- If it fails, explain what's missing
- If it's non-blocking (section 13), note it but don't block

Output: the checklist with pass/fail annotations and a go/no-go
recommendation.
```

---

## Prompt 6: Cross-Cutting Change

Use this when a change affects the monorepo infrastructure (CI scripts,
contract, templates) rather than a single subproject.

```
I need to make a cross-cutting change to the monorepo:
[DESCRIBE THE CHANGE].

Per the design doc (infrastructure/docs/design.md, Winters et al. "Large-scale
changes"): cross-cutting changes must be atomic across all affected
subprojects. Don't leave the repo in a half-migrated state.

Steps:
1. Identify all affected subprojects
2. Make the infrastructure change (ci/, infrastructure/templates/, etc.)
3. Update every affected subproject atomically
4. Verify: run infrastructure/ci/run-project-ci.sh for each affected subproject
5. Commit as a single change with a clear description of what changed
   and why
```

---

## Prompt 7: Refactoring Under Test Coverage

Use this when restructuring code in a subproject without changing
behavior (from osgocean lessons).

```
I want to refactor [DESCRIBE WHAT] in projects/[PROJECT_NAME]/.

Before making any structural change:
1. Check if characterization tests exist for the code being refactored
2. If not, write characterization tests that pin the current behavior
   (golden files or assertion-based)
3. Verify all tests pass before the refactor
4. Make the structural change (separate commits from behavior changes)
5. Verify all tests still pass with identical output
6. If golden files changed, the refactor changed behavior — investigate

The refactoring must be a separate commit from any behavior change
(Fowler). Tag commit messages with refactor: prefix.
```

---

## Prompt 8: Architecture Review

Use this periodically to assess a subproject's architecture.

```
Perform an architecture review of projects/[PROJECT_NAME]/ following
the principles in infrastructure/templates/new-project/ARCHITECTURE.md.

Assess:
1. Seam map: where are the architectural boundaries? Are strategies
   extracted or hardcoded?
2. Domain abstractions: are the right concepts modeled? Any missing?
3. Coupling: count dependencies per module. Any god modules?
4. Cohesion: can every file be named in one phrase?
5. Component principles (Martin): REP, CCP, CRP, ADP, SDP, SAP
6. "How it should have been": with current knowledge, what would the
   ideal architecture look like?

Output: update ARCHITECTURE.md with findings, update TODO.md with
any new technical debt items.

Should I include other principles from other authors? If yes, list
the authors and why.
```
