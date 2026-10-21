# gdkm — Development Rules

Rules for writing and reviewing gdkm code. Loaded automatically
at the start of every session. See CodeReview.md for detailed catalog,
examples, and Fowler refactoring references.

## gdkm Overrides

The rules in this section take precedence over the generic rules further
down this file, and over the matching "Key rules for subprojects" in the
monorepo's root `CLAUDE.md`. They exist because gdkm is a standalone command-line tool:
it ships as **one Python script** that runs anywhere with `python3` and
`python3-tomlkit` installed, and can be copied, packaged or installed as a
single file. The only other way to ship a single artifact was Rust (one
binary), which was judged too heavy for a ~1,200-line tool that mostly glues
the GitHub API to a config file.

- **Single file, not one file per responsibility.** All code lives in
  `src/gdkm.py`. This overrides "One file, one responsibility … exceeds ~400
  lines, split it", "Physical and logical design align" and the "God files"
  smell. Separation of concerns is carried by **classes** instead of files:
  each class has one responsibility (`PublicKey`, `Repo`, `Config`,
  `GitHubClient`, `KeyManager`, `GitHubScanner`, `ConfigMerger`, `RepoList`,
  `Cli`, …), and each class depends only on classes defined above it, so
  dependencies stay acyclic within the file. The file-level
  `# pylint: disable=too-many-lines` is a consequence of this rule and is
  allowed.
- **Object-oriented design.** This overrides "Free functions and parameter
  objects are the default. Use classes only when there is a genuine is-a
  relationship". gdkm deliberately uses a conventional OO design: frozen
  dataclasses as value objects, service classes for behaviour, an exception
  hierarchy, and dependency injection at the seams (`GitHubClient` takes a
  transport and a token provider so tests can replace them). Composition is
  still preferred over inheritance: inheritance is used only for the
  exceptions.
- **Dependencies: stdlib and distribution packages only.** No PyPI, no
  virtualenvs, no vendoring. Runtime dependencies are `python3-tomlkit` and
  the `gh` CLI (for `gh auth token`). Linters and formatter (`black`,
  `flake8`, `pylint`) also come from distribution packages.
- **Lint gate.** `make lint` must pass with `black --check`, `flake8`
  (max line length 88) and `pylint` at 10.00/10. A pylint disable must be
  narrow in scope and carry a comment saying why.
- **Tests never touch the network.** Tests run against the in-memory fake
  GitHub in `tests/fakes.py` and a fake token provider; they never call the
  real `gh` or `api.github.com`.

If gdkm stops being a single-script tool (for example, if it grows into a
reusable library), drop these overrides and follow the generic rules.

## Prerequisite: License

**No commit may be made to this repository before a license is chosen.**
Create a `LICENSE` file at the repository root before the first commit.
If the project is part of a monorepo, each subproject must have its own
`LICENSE` file (see `infrastructure/docs/design.md`). If the license has not
been chosen yet, do not commit any code — discuss the license choice with
the maintainer first.

## Branch Strategy

- **main**: release branch. Commits to main happen only through merge
  commits from feature/work branches.
- **All work happens in branches.** Branch from main, work in the branch,
  merge back to main with a merge commit. No direct commits to main.
- **Short-lived branches** (Fowler). Merge frequently. Don't let branches
  diverge far from trunk. Every merge to main triggers the CI pipeline.

## Architecture

- **Entry point is glue only.** Parse arguments, delegate to modules. No
  callback longer than ~20 lines.
- **One file, one responsibility** (Martin: Single Responsibility Principle).
  If a file has 3+ concerns or exceeds ~400 lines, split it. Name each
  file so its purpose is obvious in one phrase.
- **Minimize coupling** (Booch). If A.h includes B.h for a single type,
  that type belongs in its own header. Count dependencies per module;
  if a module has 5+ project-internal includes, it may be doing too much.
- **Physical and logical design align** (Lakos). Directory structure
  mirrors module/component structure. No "utils" junk drawers.
- **Acyclic dependencies** (Lakos, Martin ADP). No cycles between modules,
  between packages, between subprojects. If a cycle appears, break it by
  extracting the shared dependency or inverting via an interface.

## Design Principles

- **YAGNI** (Beck). Don't build abstractions for hypothetical future needs.
  Refactor when the need is concrete, not before. Three concrete cases
  before you generalize.
- **Simple Design** (Beck). In order: passes tests, reveals intention,
  no duplication, fewest elements.
- **Once and Only Once.** Every piece of logic has one authoritative
  location. If you copy-paste, extract a function.
- **Favor composition over inheritance** (Gamma). Free functions and
  parameter objects are the default. Use classes only when there is a
  genuine is-a relationship.
- **Encapsulate what varies** (Gamma). Identify the parts that change and
  isolate them behind stable interfaces. Don't abstract things that
  don't vary.
- **Program to an interface, not an implementation** (Gamma). Depend on
  what a thing does, not how it does it.
- **Dependency Inversion Principle** (Martin). High-level policy should
  not depend on low-level details. Both should depend on abstractions.
- **Open/Closed Principle** (Martin/Gamma). Modules should be open for
  extension, closed for modification — at module boundaries, not
  everywhere.
- **Design for replaceability.** Each component should be replaceable
  without modifying its consumers. Use strategy patterns at seams where
  behavior varies. Do not introduce abstractions speculatively — extract
  an interface when a second implementation appears, not before.

## SOLID Principles (Martin)

- **S — Single Responsibility.** Each module has one reason to change.
- **O — Open/Closed.** Extend via new code, not by modifying existing code.
- **L — Liskov Substitution.** Any implementation must honor its
  interface's full contract.
- **I — Interface Segregation.** Don't force consumers to depend on
  interfaces they don't use. Keep public APIs narrow.
- **D — Dependency Inversion.** Depend on abstractions, not concretions.

## Component Principles (Martin)

When deciding what belongs together in a module or subproject:

- **REP (Reuse-Release Equivalence).** The unit of reuse is the unit of
  release. Each module must be independently releasable and useful.
- **CCP (Common Closure).** Gather things that change for the same reasons
  and at the same times.
- **CRP (Common Reuse).** Don't force consumers to depend on things they
  don't use.

When managing dependencies between modules:

- **ADP (Acyclic Dependencies).** The dependency graph must be a DAG.
- **SDP (Stable Dependencies).** Depend in the direction of stability.
- **SAP (Stable Abstractions).** Stable packages should be abstract.

## Resource Management

- **RAII for all external resources.** Tie resource lifetime to object
  lifetime. No manual open/close, no manual free/join outside
  destructors or RAII wrappers.
- **Checked API wrappers.** Wrap C APIs with helpers that check return
  codes. No unchecked calls to functions that can fail.
- **Guard nullable APIs.** Functions that can return NULL (getenv(),
  getpwnam(), etc.) must be checked before use.

## Error Handling

- **Throw on failure, catch at the boundary.** Internal modules throw
  on error. The entry point catches once. No shared mutable error flags.
- **Show useful output on failure.** Error messages must include what
  failed, where, and the underlying error detail.
- **Throw with context.** Include what was attempted, the target
  (hostname, path, identifier), and the error (exit code, API error
  string).

## Testing

### Test First (Beck + osgocean lessons)

- **Test-first for new data types and parsers.** Any new enum, struct,
  or parse function must have a test written BEFORE the implementation.
  The test defines the contract; the implementation satisfies it.
- **Golden files as regression gate.** Any change to deterministic output
  must update golden files. Reviewers verify the diff is intentional.
- **Characterization tests for existing code.** Before refactoring, pin
  the current behavior with tests. Refactoring means changing structure
  without changing behavior — tests prove it.

### Guard Against Regressions at Every Level (osgocean lessons)

- **Computation regressions.** Deterministic output for fixed inputs
  must remain identical. Golden files catch drift.
- **Interface regressions.** Once an interface is published, changing its
  signature is a breaking change (Hyrum's Law — Winters et al.). Extend,
  do not modify.
- **Performance regressions.** If a change affects performance, measure
  before and after. Do not introduce unnecessary allocations, copies, or
  indirection in hot paths.

### General Testing Rules

- **Changing a test requires justification.** Before modifying an
  existing test to make it pass, ask: does the test exist for a good
  reason? If the test caught a real invariant, fix the code, not the
  test. Only change the test if the requirement genuinely changed — and
  say so in the commit message.
- **Don't break the build.** The build must succeed with no errors.
  Warnings from project source files should be fixed.
- **Static analysis clean.** Linters and static analyzers must pass
  with zero errors on project code. Use a "no new warnings" baseline for
  existing code. Fix real bugs (null dereferences, leaks, undefined
  behavior); defer style modernization in code about to be refactored.

## Code Smells to Avoid

- **God files.** Split when a file handles multiple domains.
- **Copy-pasted blocks.** Extract a helper immediately.
- **Magic numbers.** Use named constants.
- **Dead code.** Remove it, wire it up, or triple-mark it (see "Dead
  code and stubs" below). Never leave it unmarked.
- **Primitive obsession.** Consider enums or types for strings that are
  compared in multiple places.
- **Feature envy.** If a function uses more data from another module's
  types than its own, it may belong in that module.
- **Long parameter lists.** If 5+ parameters travel together, use a
  parameter object (Fowler: Introduce Parameter Object).

## Dead Code and Stubs

Dead code, stub commands, and untested code may exist but MUST be
marked in all three places:

1. **In the code.** The function must have a comment: `// [STUB] ...`
   or `// [DEAD CODE] ...` with a one-line reason and a cross-reference
   to the user story or issue that will complete it.
2. **In the documentation.** TODO.md must list the item in the "Stubs
   and dead code audit" section with its status and what is missing.
3. **At runtime.** When a user invokes a stub command, the output must
   include `[stub]` and say what is not implemented. A stub must NEVER
   silently succeed.

## Technical Debt

- **Track it.** Every shortcut gets a TODO.md entry with a label and a
  note about why. Classify using Fowler's quadrant: deliberate/prudent
  is acceptable; reckless or inadvertent debt should be fixed promptly.
- **Don't accumulate it silently.** If you take a shortcut, say so in
  the commit message and the TODO.

## Continuous Integration (Humble + Farley)

- **Everything in version control.** Source, tests, CI configuration,
  infrastructure scripts, documentation — all in the repo. No tribal
  knowledge.
- **Automate everything.** The pipeline is the single source of truth
  for "how to build and validate this."
- **Fast feedback.** The commit stage (lint, build, test) should complete
  in under 10 minutes. Parallelize aggressively.
- **Never skip the pipeline.** Even for "trivial" changes. The pipeline
  is the only authority on whether a change is safe.
- **Build once, promote the artifact.** Don't rebuild for different
  environments.

## Commits

- One logical change per commit. Refactoring commits must not change
  behavior. Enhancement commits must not restructure code.
- Commit messages: imperative mood, short subject line, body explains
  why not what.
- Always use: `git commit --signoff`
- Author: set identity via env vars on every commit (see global
  CLAUDE.md for identity).

## References

- CodeReview.md — full code smell catalog, design patterns, Fowler
  refactoring catalog, review checklist
- ARCHITECTURE.md — module responsibilities and design decisions
- TODO.md — implementation status, remaining work, technical debt
- USER_STORIES.md — requirements and acceptance criteria
- TestPlan.md — test plans
- ReleaseCriteria.md — release checklist
- ADR.md — Architecture Decision Record
- ROADMAP.md — development phases and future plans
