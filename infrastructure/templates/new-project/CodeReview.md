# {{PROJECT_NAME}} — Code Review Guidelines

How to conduct a code review. Reviews are logged with dates and commit
hashes.

## When to Review

- Before tagging a release
- After a significant refactor
- When resuming work after a break (re-familiarization)
- Before merging feature branches to main

## What to Check

### 1. User Stories Alignment

Compare completed user stories (USER_STORIES.md) against the code:

- Is every completed story actually implemented?
- Are there acceptance criteria that aren't met?
- Is there dead code from stories that were partially implemented
  or superseded?
- Are there implemented features that have no corresponding story?

### 2. Separation of Concerns (Booch / Lakos / Martin SRP)

Per ARCHITECTURE.md, each source file owns a single responsibility:

- Entry point should be glue only — no business logic
- Domain-specific backends should be split by domain
- Transport/IO modules should be independent of business logic
- Check for files growing beyond ~400 lines — a sign of mixed concerns
- Check for unnecessary coupling between modules
- Check include/import graphs: if a module pulls in a large dependency
  for a single type, that type should move to its own module

### 3. Code Duplication (Beck: Once and Only Once)

Look for:

- Identical or near-identical blocks across files
- Similar data generation or transformation logic duplicated between
  modules
- Repeated boilerplate patterns that should be helpers

### 4. Resource Management

- All external resources (handles, connections, file descriptors) must
  use RAII wrappers or equivalent patterns
- No manual open/close, free/join, or fclose outside destructors
- Check error paths for resource leaks

### 5. Error Handling

- API return codes checked (via checked wrappers, not inline)
- Null pointer guards on functions that can return null
- Failures show useful output, not silent swallowing
- Error messages include what failed, where, and why

### 6. Consistency

- Configuration values used everywhere they apply, not ignored in some
  code paths
- Magic numbers replaced with named constants
- Connection/session patterns uniform across the codebase

### 7. Security

Review credential handling and document accepted risks:

- Passwords in process trees or logs — are they acceptable for the
  use case?
- Inputs from external sources validated for injection (shell, SQL,
  XSS, etc.)
- Secrets not committed to version control

### 8. Documentation Alignment

- TODO.md checked items match code; unchecked items are unimplemented
- File references match current names after refactors
- ARCHITECTURE.md module table matches actual source files

## Review Output Format

Each review entry should include:

```
## Review N: <title>

**Date:** YYYY-MM-DD
**Commit:** <full hash>

### Codebase Metrics
(file line counts, concern inventory)

### Findings
(categorized: SoC violations, code smells, bugs, security, etc.)

### Proposed Actions
(prioritized: what to fix, in what order)

### Expected Impact
(before/after metrics)
```

## Severity Levels

| Category | Severity | Action |
|---|---|---|
| Separation of concerns violations | High | Fix before next release |
| Security issues (beyond accepted risks) | High | Fix immediately |
| Missing error handling | Medium | Fix before next release |
| Code duplication | Medium | Fix in next refactor pass |
| Shared mutable error state | High | Replace with exceptions or type-system guarantee |
| Manual resource cleanup outside RAII | High | Wrap in RAII |
| Comment-enforced invariant | Medium | Type-system guarantee |
| Stubs that exit 0 (silent success) | Medium | Triple-mark: error, document, label |
| Inconsistencies | Low | Fix opportunistically |
| Dead code | Low | Triple-mark or remove |
| Documentation staleness | Low | Fix when touching related code |

## Code Smell Catalog

Patterns to look for during every review. Each has a label for tracking
in TODO.md. The "Fowler fix" column references the refactoring technique
from the catalog below.

### Separation of Concerns

**SoC-1: Business logic in glue layer**
- Entry point should only parse arguments and delegate.
- Detected by: line count of callbacks in main/entry point.
- Fowler fix: Extract Method, Move Method, Extract Class.

**SoC-2: God file (single file with multiple unrelated responsibilities)**
- A file handling more than one domain will grow unmanageable.
- Detected by: file exceeding ~400 lines, or listing 3+ distinct
  concerns.
- Fowler fix: Extract Class, Move Method. Smell: Divergent Change.

**SoC-3: Coupling via unnecessary dependencies**
- If module A depends on module B only for a single type, that type
  should live in its own module.
- Detected by: imports/includes that pull in a large module for a
  single type or function.
- Fowler fix: Extract Class (extract the shared type).

**SoC-4: Inconsistent resource management patterns**
- Multiple patterns for the same operation make the code harder to
  audit and more likely to leak resources on error paths.
- Fowler fix: Replace Constructor with Factory Method, Introduce
  Parameter Object (RAII wrapper).

### Code Duplication

**CS-1: Copy-pasted logic blocks**
- Identical multi-line blocks appearing in multiple functions.
- Fowler fix: Extract Method.

**CS-2: Duplicated data generation**
- Two functions generating the same structured output with minor
  differences.
- Fowler fix: Extract Method, Parameterize Method, Form Template
  Method.

### Error Handling

**CS-3: Unchecked API return codes**
- API calls that return error codes which are silently ignored.
- Fowler fix: Replace Error Code with Exception (checked wrapper).

**CS-5: Unguarded nullable APIs**
- Functions that can return null, passed directly to code that
  doesn't accept null.
- Fowler fix: Introduce Assertion, Replace Exception with Test.

### Configuration Inconsistencies

**CS-4: Config value defined but not used**
- A config accessor exists but isn't used in all relevant code paths.
- Fowler fix: Remove Parameter, Preserve Whole Object.

**CS-6: Inconsistent config sourcing**
- Some code paths read from config, others use hardcoded defaults for
  the same setting.
- Fowler fix: Introduce Parameter Object, Preserve Whole Object.

### Magic Values

**CS-7: Undocumented magic numbers**
- Numeric literals in logic with no explanation.
- Fowler fix: Replace Magic Number with Symbolic Constant.

### Type Safety

**CS-15: Stringly typed domain concepts**
- Domain concepts compared as bare strings in multiple files. A typo
  is a silent bug.
- Fowler fix: Replace Data Value with Object (enum/type).

### Dead Code

**CS-9: Unused variables or functions**
- Variables assigned but never read, or functions never called.
- Fowler fix: remove the dead code, or Inline Method.

### Unused Data

**CS-17: Boat anchor (parsed but unconsumed fields)**
- Fields parsed into data structures but never read by consumer code.
  Violates YAGNI.
- Fowler fix: remove the field, or wire it to actual functionality.

## Design Patterns Guidance

### Currently Applicable Patterns

**RAII (Resource Acquisition Is Initialization)**
Tie resource lifetime to object lifetime. Destructor guarantees cleanup.

**Facade**
Simplified interface to a complex subsystem. A single function hides
multi-step orchestration. A facade is not a God class: it owns and
configures its components but does not contain their logic.

**Strategy**
Different backends or algorithms implement the same interface. The
consumer calls through the interface, not a concrete class. Extract
an interface when the second implementation appears, not before (YAGNI).

**Repository (data access)**
Centralize data access behind a typed API. Consumers never write raw
queries outside the repository module.

**Builder / Parameter Object**
When a function grows beyond 5 parameters, introduce a config struct
or builder. Name the concept the parameters describe.

### Patterns to Consider Adopting

**Observer / Event Bus**: when notification calls would scatter through
the code.

**Command**: when operations need execute/verify/rollback semantics.

**Chain of Responsibility / Pipeline**: when a hardcoded processing
sequence should be configurable.

**Factory**: when if/else chains dispatch on type strings. A factory
mapping types to implementations is cleaner and extensible.

**Adapter**: when multiple implementations of a transport or protocol
need the same result interface.

## Refactoring Catalog

Reference catalog of refactoring techniques from Martin Fowler's
*Refactoring: Improving the Design of Existing Code*. During each
review, consider whether any of these apply.

### Composing Methods

| Technique | Description |
|---|---|
| Extract Method | Pull a code fragment into its own method |
| Inline Method | Replace a method call with the body when the body is clearer |
| Replace Temp with Query | Replace a temp with a method call |
| Introduce Explaining Variable | Give a complex expression a meaningful name |
| Replace Method with Method Object | Turn a long method into its own class |

### Moving Features Between Objects

| Technique | Description |
|---|---|
| Move Method | Move a method to the class that uses it most |
| Extract Class | Split a class doing two things into two classes |
| Inline Class | Merge a class that isn't doing enough |
| Hide Delegate | Create a method on the server to hide the delegate |

### Organizing Data

| Technique | Description |
|---|---|
| Replace Magic Number with Symbolic Constant | Named constant instead of bare number |
| Replace Data Value with Object | Turn a primitive into a type |
| Replace Type Code with Class | Type code to class for compile-time checking |
| Introduce Parameter Object | Group of traveling parameters to an object |

### Simplifying Conditional Expressions

| Technique | Description |
|---|---|
| Decompose Conditional | Extract condition and branches into methods |
| Replace Nested Conditional with Guard Clauses | Early returns instead of nesting |
| Replace Conditional with Polymorphism | Polymorphic dispatch instead of type switches |

### Simplifying Method Calls

| Technique | Description |
|---|---|
| Rename Method | Name that reveals purpose |
| Preserve Whole Object | Pass the object instead of extracting values |
| Replace Error Code with Exception | Throw instead of returning error codes |

### Handling Divergent Change and Shotgun Surgery

**Divergent Change**: one file changed for multiple unrelated reasons.
Sign of a god class. Fix: Extract Class.

**Shotgun Surgery**: one logical change requires edits in many files.
Sign of a scattered concern. Fix: Move Method, Inline Class.

## Review Checklist

Consolidated checklist for every code review.

### Correctness
- [ ] Do completed user stories match the code? Any unmet criteria?
- [ ] Are there dead code paths or stub commands to wire up?

### Test Discipline (Beck)
- [ ] New data types or parse functions: was the test written BEFORE
      the implementation?
- [ ] Any test modified to "make it pass"? Verify the change is
      warranted by a genuine requirement change.
- [ ] Golden files updated? Diff reviewed for intentional changes?
- [ ] Characterization tests written before refactoring? (osgocean lesson)

### Architecture (Lakos / Booch / Martin)
- [ ] Is the entry point glue-only?
- [ ] Any file > 400 lines or with 3+ concerns?
- [ ] Any unnecessary coupling between modules?
- [ ] Component cohesion: REP, CCP, CRP satisfied? (Martin)
- [ ] Dependency graph acyclic? (Martin ADP, Lakos levelization)

### Safety
- [ ] All API return codes checked?
- [ ] All resource handles RAII-wrapped?
- [ ] Null guards on nullable APIs?
- [ ] Credential handling reviewed?
- [ ] External input validated for injection?

### Quality
- [ ] Any copy-pasted blocks? Extract Method.
- [ ] Any if/else chains on type strings? Factory or Strategy.
- [ ] Any function with 5+ parameters? Introduce Parameter Object.
- [ ] Any magic numbers? Replace with named constant.
- [ ] Hyrum's Law: any internal details that could be depended on
      by consumers? (Winters et al.)

### Consistency
- [ ] Config values used everywhere they apply?
- [ ] Patterns uniform across code paths?

### Documentation
- [ ] TODO.md items match code state?
- [ ] ARCHITECTURE.md module table matches source files?

### Technical Debt
- [ ] Hunt technical debt and propose paths out of it. For each item,
      identify which Fowler refactoring technique(s) apply and estimate
      the effort (trivial / small / significant).

## Foundational Principles

### Kent Beck — Simple Design (XP)

1. **Passes the tests** — code must work before it can be clean.
2. **Reveals intention** — clear naming, no puzzles for the reader.
3. **No duplication** — Once and Only Once.
4. **Fewest elements** — remove anything that doesn't serve rules 1-3.

**YAGNI**: don't build abstractions for hypothetical future
requirements. Build what's needed now, refactor when the need is
concrete.

### Gang of Four (Gamma, Helm, Johnson, Vlissides)

- **Program to an interface, not an implementation.**
- **Favor composition over inheritance.**
- **Encapsulate what varies.**

### Robert C. Martin — SOLID + Component Principles

SOLID governs internal module design. Component principles (REP, CCP,
CRP, ADP, SDP, SAP) govern inter-module structure. See CLAUDE.md for
the full list.

### Ward Cunningham — Technical Debt

Classify using Fowler's quadrant:

|  | Prudent | Reckless |
|---|---|---|
| **Deliberate** | "We know this shortcut; we'll fix it" | "We don't have time for design" |
| **Inadvertent** | "Now we know how we should have done it" | "What's layering?" |

During reviews, classify new debt and ensure it stays in the prudent
columns.

### Martin Fowler — Code Smells

Beyond the CS-N catalog above: Feature Envy, Data Clumps, Primitive
Obsession, Long Parameter List. See CLAUDE.md for descriptions.

### Grady Booch — Coupling, Cohesion, and Architecture

- **Minimal coupling**: few dependencies per module.
- **Maximal cohesion**: everything in a module relates to its single
  purpose.
- **Data bags are a smell**: a struct with many unused fields doesn't
  reveal intention.

### Jez Humble + Dave Farley — Continuous Delivery

- **Everything in version control.**
- **Automate everything.**
- **The pipeline is the only authority on whether a change is safe.**

### Titus Winters et al. — Software Engineering at Google

- **Hyrum's Law**: all observable behaviors will be depended on. Be
  deliberate about what you expose.
- **Code review as quality gate**: every change goes through review.
- **Large-scale changes**: cross-cutting changes should be atomic.
- **One version rule**: avoid version skew on shared dependencies.

## Self-Assessment Principles

During review, also evaluate:

**Is the data model honest?** A model that ships without consumers is
dead code (YAGNI applies to data structures too).

**Are the abstractions at the right level?** If the same concept is
encoded differently in different places, the abstraction may be too
scattered.

**Are compromises documented?** Every shortcut and deferred refactoring
should be traceable in TODO.md with a rationale. Undocumented debt is
reckless debt.

## Lessons from Past Reviews

(Record review lessons here as the project evolves. Include what was
found, what was done, and what principle it reinforced.)

### Process Lessons (from labforge/osgocean experience)

1. **Rules you don't follow are worse than no rules.** During review,
   check every stated rule against the code. If the code violates the
   rule, either fix the code or update the rule.
2. **DONE must mean DONE.** Status markers that lie erode trust. Verify
   every [DONE] and [COMPLETED] against the code.
3. **Documentation is not testing.** Compare test coverage to
   documentation claims.
4. **Aspirational specifications are not TODO items.** Mixing
   implemented work with aspirational design creates an illusion of
   completeness.
5. **The developer may improve on the reviewer's fix.** State the
   problem, not just the fix.
6. **Test the real pipeline, not a mock.** Exercise the same code path
   the user sees.
7. **Measure before optimizing.** Implement, benchmark, revert if no
   benefit.
8. **Review in context.** State assumptions about team size and
   constraints before making recommendations. A recommendation that
   doesn't fit the constraints is noise.
