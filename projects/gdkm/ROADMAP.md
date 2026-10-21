# gdkm — Roadmap

Development phases and detailed specifications. Separated from TODO.md
so that current priorities are visible without wading through phase
history.

For current priorities, see TODO.md.
For what works today, see ARCHITECTURE.md "Current Scope."

## Roadmap Principles

### Parallel Tracks (from osgocean)

Work is organized in two parallel tracks:

- **Track A (Refactoring)**: structural changes with no behavior change.
  Every refactoring must pass existing tests with identical results.
  Track A items create the seams that make Track B items safe and simple.
- **Track B (Enhancements)**: visible improvements and new capabilities.
  Items with no dependency can proceed at any time. Items that depend on
  a specific Track A extraction name the dependency explicitly.

This separation enforces the discipline that refactoring commits must
not change behavior, and enhancement commits must not restructure code
(Fowler).

### Incremental Delivery (Beck / Humble + Farley)

Each step is independently shippable and testable. Don't build step N+1
until step N is verified. The CI pipeline validates each step before
proceeding.

### Dependency Diagrams

Use dependency diagrams to show which items block which:

```
A0 (analysis) ── A1 (tests) ─────┬─── A2 (extraction 1) ── B1 (enhancement 1)
                                  │
                                  ├─── A3 (extraction 2) ── B2 (enhancement 2)
                                  │
                                  └─── A4 (extraction 3) ── B3 (enhancement 3)

(independent)                          B4 (standalone enhancement)
```

---

## Sequence 0: Static Analysis and Bug Fixes

Before any behavioral or structural change, fix real bugs found by
static analysis. This ensures golden files captured in Sequence 1
reflect correct behavior, not latent bugs (osgocean lesson).

### A0. Run static analysis, fix bugs only

**Fix:** null dereferences, uninitialized variables, resource leaks,
undefined behavior.

**Ignore (for now):** modernization suggestions and style warnings in
code about to be refactored. That is churn, not improvement.

**Add to CI:** so new code is checked automatically. Use a "no new
warnings" baseline.

---

## Sequence 1: Test Infrastructure

Pin the current behavior so that regressions are caught automatically.

### A1. Characterization tests

- **Unit tests**: fixed inputs, compare output against golden reference
  files with appropriate tolerance.
- **Integration tests**: end-to-end workflow verification.
- **Golden files**: checked into `tests/golden/`.
- **CI integration**: register all tests. Tests that require
  unavailable resources (GPU, network, hardware) must skip, not fail.

---

## Sequence 2: Refactoring (Track A)

Extract replaceable strategies from hardcoded implementations. Each
step changes structure without changing behavior. Every refactoring
must pass the characterization tests from Sequence 1 with identical
results.

### A2-AN. Extractions

(Document each extraction with: what was extracted, the interface it
now uses, what the extraction revealed about the design.)

---

## Sequence 3: Enhancements (Track B)

Each item changes what the code produces. Items with no dependency can
proceed at any time. Items with a dependency name the specific
refactoring step required.

### B1-BN. Enhancements

(Document each enhancement with: what it does, which extraction it
depends on, references to relevant literature or prior art.)

---

## Sequence 4: Architecture Review

After the initial extractions and enhancements, use empirical
experience to validate or revise the target architecture.

### AN+1. Document the target architecture

1. Validate or revise the domain abstractions. What was predicted vs
   what was learned?
2. Define the collaborations. Who creates each object? Who holds it?
3. Identify the next extractions. The architecture predicts what should
   be extracted next.

The output is a documented target architecture — not a spec to
implement blindly, but a hypothesis to test with each subsequent
extraction (osgocean lesson).

---

## Future Phases

(Placeholder for phases not yet specified. Each phase should follow
the same pattern: static analysis, tests, refactoring, enhancements,
review.)

---

## Release Milestones

### vX.0 — First milestone

(Describe what "done" looks like for the first release. What's in,
what's not.)

### vX+1.0 — Second milestone

(Build on the first. What new capabilities are added?)

---

## Deferred

Items that are architecturally significant but not yet justified by a
proven bottleneck or user need (Beck: YAGNI):

- Item. Do when: condition that triggers the work.
- ...

---

## Dependency Diagram (Full)

```
(Draw the full dependency diagram here as the roadmap fills in.)
```
