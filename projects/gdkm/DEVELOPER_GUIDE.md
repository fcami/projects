# gdkm — Developer Guide

## Architecture Overview

See `ARCHITECTURE.md` for the full design document. This guide covers
practical development workflow.

```
src/                    Source files (one file per concern)
tests/                  Tests (unit, integration, golden files)
tests/golden/           Golden reference files for regression testing
docs/                   Additional documentation
```

## Build

```bash
# (Insert build commands here)
# All dependencies from standard package sources — no network fetches
# during build unless explicitly documented
```

The build must be reproducible from a clean checkout (Humble + Farley:
everything in version control, automate everything).

## Source Structure

Each source file owns a single responsibility (Martin: SRP):

| File | Responsibility | Key APIs |
|---|---|---|
| `entry_point` | CLI/API definition, delegates to modules | `main()` |
| `...` | ... | ... |

(Fill in as the project grows. This table should match
ARCHITECTURE.md.)

### Adding a New Module

1. Create the source file(s)
2. Add to the build system
3. Accept context/config as a parameter — don't reach into global state
   (Gamma: make dependencies explicit)
4. Follow the project's verbosity/dry-run pattern if applicable
5. Write tests BEFORE the implementation (Beck: TDD)
6. Run linters before committing

## Patterns in Use

(Document the language-specific patterns used in the project. These
are the patterns a new contributor needs to recognize.)

### Error Handling

(Document the error handling strategy: exceptions, Result types,
error codes with checked wrappers, etc.)

### Resource Management

(Document the RAII strategy: wrappers, smart pointers, context
managers, defer, etc.)

### Configuration

(Document how configuration is loaded, stored, and accessed.
Single source of truth per setting.)

## Testing

### Running Tests

```bash
# Run all tests
(test command)

# Run specific test
(specific test command)

# Run only fast tests (no external dependencies)
(fast test command)
```

### Writing Tests

- **New data types / parsers**: test BEFORE implementation (Beck: TDD)
- **Golden files**: checked into `tests/golden/`. Update with the
  regeneration script after intentional changes.
- **Characterization tests**: pin current behavior BEFORE refactoring
  (osgocean lesson)
- **Integration tests**: exercise the real pipeline, not a mock
  (osgocean lesson)

### Static Analysis

```bash
# (Insert static analysis commands here)
```

Run on changed files. Fix bugs (null dereferences, leaks, undefined
behavior). Defer style modernization in code about to be refactored
(osgocean lesson: that's churn, not improvement).

## Git Conventions

### Branch Strategy

- Work in feature branches, merge to main with merge commits
- Short-lived branches — merge frequently (Fowler)
- Every merge to main triggers CI

### Commits

- One logical change per commit
- Refactoring commits must not change behavior
- Enhancement commits must not restructure code
- Commit messages: imperative mood, short subject line, body explains
  why not what
- Always use: `git commit --signoff`
- Set identity via env vars on every commit (see global CLAUDE.md)

### Pre-push Hook

(If the project has a pre-push hook, document how to install and use
it. Document how to bypass for emergencies.)

## Planned Work

See `TODO.md` for the current priority list.
See `ROADMAP.md` for the full phased plan.
See `USER_STORIES.md` for requirements and acceptance criteria.

## Continuous Integration (Humble + Farley)

- The CI pipeline is the authority on whether a change is safe
- The commit stage (lint, build, test) should complete in under
  10 minutes
- Everything needed to build and test is in the repository — no
  external state, no tribal knowledge
- A new contributor should be able to clone, build, and run all tests
  by following only this guide
