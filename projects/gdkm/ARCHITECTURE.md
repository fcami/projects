# gdkm — Architecture

## Current Scope

(Describe what the project does today. What works and is tested. What
is implemented but unverified. What is not implemented. Update this
section with every release.)

## Design Principles

### Separation of Concerns (Booch / Lakos / Martin SRP)

Each source file owns a single responsibility. No file should mix
concerns.

| File | Responsibility |
|---|---|
| `entry_point` | CLI/API definition only, delegates to modules |
| `config` | Load and validate configuration |
| `...` | ... |

(Fill in the module table as the project grows. This table IS the
architecture. If a module appears in the codebase but not in this
table, it doesn't have a defined responsibility.)

### Physical Design (Lakos)

- Directory structure mirrors module/component structure.
- No circular dependencies between modules. The dependency graph is a
  DAG.
- Each module is testable in isolation.
- Transitive dependencies minimized: depend only on what you directly
  use.

### Component Principles (Martin)

- **Cohesion**: modules follow REP (independently releasable), CCP
  (change together), and CRP (no forced dependencies).
- **Coupling**: dependency graph is acyclic (ADP). Dependencies point
  toward stability (SDP). Stable modules are abstract (SAP).

### Design for Replaceability (Gamma / osgocean lessons)

Each component should be replaceable without modifying its consumers:

- Identify the parts that vary (algorithms, backends, transport
  mechanisms, formats). These are the seams where abstraction belongs.
- Use strategy patterns at seams. Don't abstract things that don't vary.
- Do not introduce abstractions speculatively. Extract an interface when
  a second implementation appears.

### Dependency Rule (Martin: Clean Architecture)

Dependencies point inward — from volatile, concrete outer layers toward
stable, abstract inner layers. I/O and framework code depend on domain
logic, never the reverse.

## Seam Map

(Document where each architectural seam exists, what crosses it, and
what implementations exist. Update as extractions occur.)

```
Module A
    |
    | seam: Interface name
    | crosses: input → output
    | called: when / how often
    | implementations: Impl1, Impl2
    |
    v
Module B
```

### What the seams reveal

(After extracting strategies or interfaces, document what the
extraction taught about the design. From osgocean: "A2 revealed the
spectrum function receives pre-computed intermediates rather than
physical parameters — this is the correct design." These lessons
prevent future regressions of understanding.)

## Domain Abstractions

(List the domain concepts identified during review and development.
For each, note its status and where it currently lives.)

| Abstraction | Status | Where it lives now |
|---|---|---|
| ... | Extracted / Not extracted / Partially extracted | File or module |

### Predicted Next Extractions

(Based on the seam map and domain abstractions, what should be
extracted next? These are hypotheses to test, not mandates.)

## Directory Layout

```
{{project_name}}/
├── src/                    Source files (one per concern)
├── tests/                  Tests
│   └── golden/             Golden reference files
├── docs/                   Additional documentation
├── ARCHITECTURE.md
├── CLAUDE.md
├── README.md
├── LICENSE
└── ...
```

## Key Types / Interfaces

(Document the central data structures and interfaces. Show them as
code or pseudocode. This section is the type-level contract.)

## Build System

(Document build dependencies, build commands, and the rule that all
dependencies must be satisfiable from the project's ecosystem — no
network fetches during build unless explicitly documented.)

### Linting and Static Analysis

All code must pass linters and static analyzers before commit:

- List language-specific tools here
- Use a "no new warnings" baseline for existing code (osgocean lesson:
  don't fix style warnings in code about to be refactored)

### Output Verbosity / Dry-Run

(If the project has CLI output, document verbosity levels and dry-run
behavior.)

## Architecture Decision Record

See ADR.md for significant decisions and their rationale. Captured so
that future decisions can be evaluated against the same criteria, and
so that the reasoning survives beyond the developer's memory.

## Lessons Learned

(Record architectural lessons discovered during development. From
labforge: "Rules you don't follow are worse than no rules." From
osgocean: "Test the real pipeline, not a mock." These survive for
future contributors.)

### How It Should Have Been

(After significant refactoring or at architecture review points,
document "how it should have been" — the ideal architecture given what
was learned. This is a hypothesis for future work, not a spec to
implement blindly. From osgocean: "OceanScene should be a Facade, not
a God class.")
