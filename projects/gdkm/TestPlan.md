# gdkm — Test Plans

## Test Principles

### Test First (Beck)

No code change without a way to verify it. Before modifying behavior,
ensure a test pins the current behavior. Before adding a feature, write
a test that defines its contract.

### Guard Against Regressions (osgocean lessons)

- **Computation regressions**: deterministic output for fixed inputs
  must remain identical. Golden files catch drift.
- **Interface regressions**: changing a published interface's signature
  is a breaking change. Extend, do not modify.
- **Performance regressions**: measure before and after changes that
  affect hot paths.

### Test the Real Pipeline (osgocean lesson)

Exercise the same code path the user sees. A mock or simplified test
binary may produce results that look nothing like the real application.

### Characterization Tests Before Refactoring (osgocean lesson)

Before restructuring code, pin the current behavior with tests. If no
tests exist for the code being refactored, write characterization
tests first — capture the current output, then restructure. The tests
prove the refactoring preserved behavior.

### Measure Before Optimizing (osgocean lesson)

Don't assume an optimization helps. Implement, benchmark, and revert
if there's no measurable benefit. Keep the benchmark tool for future
platforms.

## Test Types

### Unit Tests

- Pure computation, no external dependencies
- Fixed inputs, compare against golden reference files
- Tolerance-based comparison for floating-point output
- Registered with the test runner, labeled by type

### Integration Tests

- End-to-end workflow verification
- May require external resources (database, network, hardware)
- Tests that require unavailable resources must skip, not fail

### Golden File Tests

- Deterministic output captured as reference files in `tests/golden/`
- Any change to output must update golden files
- Reviewers verify the diff is intentional
- Regeneration script provided (e.g., `golden_update.sh`)

### Static Analysis

- Integrated into CI build
- "No new warnings" baseline for existing code
- Fix real bugs; defer style modernization in code about to be
  refactored

---

## Smoke Test

Quick verification that the core pipeline works end-to-end. Suitable
for post-refactor checks and routine validation.

### Prerequisites

(List what must be in place before running the smoke test.)

### Steps

## 1. Build verification

```
(build commands)
```

- [ ] Compiles with no errors
- [ ] No warnings from project source files

## 2. Read-only / query commands

```
(read-only commands)
```

- [ ] Expected output produced
- [ ] No errors

## 3. Dry-run or preview

```
(dry-run commands)
```

- [ ] Correct output produced
- [ ] No side effects

## 4. Full workflow

```
(full workflow commands)
```

- [ ] Workflow completes successfully
- [ ] Output matches expectations

## 5. Cleanup / teardown

```
(cleanup commands)
```

- [ ] All artifacts removed
- [ ] Clean state restored

---

## Full Test Plan

Comprehensive validation covering the entire project lifecycle, error
handling, and edge cases. Run before releases or after significant
changes.

### Prerequisites

(List requirements: clean state, available resources, etc.)

### Steps

(Expand each step with commands and checkboxes. Cover:
1. Clean state
2. Configuration
3. Normal workflow (happy path)
4. Error handling (invalid inputs, missing resources)
5. Edge cases
6. Lifecycle operations
7. Cleanup)

---

## CI Integration (Humble + Farley)

- All tests run on every push and PR
- Fast tests (unit, lint) run first for fast feedback
- Slow tests (integration, end-to-end) run after fast tests pass
- Tests that require unavailable resources skip with clear message
- Pipeline must complete in under 10 minutes for the commit stage
- Pipeline results are the authority on whether a change is safe
