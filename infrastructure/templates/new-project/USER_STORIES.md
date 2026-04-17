# {{PROJECT_NAME}} — User Stories

> **WARNING: changing user stories**
>
> User stories in this document must NEVER be removed without explicit
> human approval. User stories must NEVER be reworded without human
> analysis and confirmation. If a story needs updating, add a new version
> below the original with a date and rationale — do not edit in place.
>
> New user stories must be reviewed and approved by the user before being
> committed. Do not invent requirements or add stories without explicit
> request.
>
> Moving a story from Todo to Completed requires all acceptance criteria
> to be met. If any criterion is not met, the story stays in Todo.

---

## How to Write User Stories

Each story follows the format:

```
### US-NNN: Title

As a <role>, I want <capability>, so that <benefit>.

**Acceptance criteria:**
- Criterion 1
- Criterion 2
- ...
```

### Principles for good stories (Beck / Martin)

- **Independent**: each story can be implemented without depending on
  another story being done first. If dependencies exist, document them.
- **Negotiable**: stories are conversation starters, not contracts. The
  acceptance criteria define the contract.
- **Valuable**: each story delivers value to the user. Infrastructure
  stories are acceptable but must explain what user-visible capability
  they enable.
- **Estimable**: the story must be concrete enough to estimate effort.
- **Small**: a story that takes more than a week should be split.
- **Testable**: every acceptance criterion must be verifiable. If you
  can't write a test for it, it's not a criterion — it's a wish.

### Component alignment (Martin: REP)

Each story should map to a coherent unit of release. If a story requires
changes to unrelated modules with no shared purpose, it may be two
stories.

---

## Completed

(Move stories here when ALL acceptance criteria are met.)

---

## In Progress

(Stories actively being worked on.)

---

## Todo

(Stories approved but not yet started.)

---

## Future

(Stories identified but not yet approved or estimated. These are
placeholders for discussion, not commitments.)

---

## Rejected / Superseded

(Stories that were considered but rejected, or replaced by a different
approach. Keep them here with a rationale so the reasoning survives.)
