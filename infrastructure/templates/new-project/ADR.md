# {{PROJECT_NAME}} — Architecture Decision Record

Significant decisions and their rationale. Captured so that future
decisions can be evaluated against the same criteria, and so that the
reasoning survives beyond the developer's memory (Booch review
recommendation).

## How to Record Decisions

Each row captures:
- **Decision**: what was chosen
- **Why**: the rationale (constraints, trade-offs, principles invoked)
- **Alternatives rejected**: what else was considered and why it lost

A decision without a rationale is just a fact. The rationale is what
lets future contributors evaluate whether the decision still holds when
constraints change.

## Principles for Decision-Making

- **YAGNI** (Beck): choose the simplest option that works now. Don't
  choose complexity for hypothetical future needs.
- **Reversibility**: prefer reversible decisions. Irreversible decisions
  warrant more deliberation.
- **Dependency Inversion** (Martin): when choosing between options,
  prefer the one that keeps high-level policy independent of low-level
  details.
- **Stable Dependencies** (Martin SDP): depend on things that change
  less often than you do.
- **Hyrum's Law** (Winters et al.): any observable behavior of a
  decision will eventually be depended on. Be deliberate about what
  behaviors your choices expose.

## Decisions

| Decision | Why | Alternatives rejected |
|---|---|---|
| ... | ... | ... |

(Add rows as decisions are made. Keep this table as a living document.)
