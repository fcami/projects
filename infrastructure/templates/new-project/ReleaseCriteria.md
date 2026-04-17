# {{PROJECT_NAME}} — Release Criteria

Checklist that must be satisfied before tagging a release. Every item
reflects a principle from the project's engineering canon (attributed
in parentheses where non-obvious).

## 1. License

- [ ] `LICENSE` file exists at the repository root
- [ ] License is appropriate for the project's distribution model
- [ ] If the project depends on libraries with copyleft licenses (GPL,
      LGPL), compatibility has been verified

## 2. Build

- [ ] Build succeeds with zero errors
- [ ] No warnings from project source files

## 3. Tests

- [ ] All tests pass
- [ ] Golden files are up to date with current output
- [ ] No tests were modified to "make them pass" without a genuine
      requirement change documented in the commit message (Beck: tests
      define the contract)
- [ ] Static analysis passes with zero errors on project code

## 4. Smoke Test

The smoke test from TestPlan.md must pass end-to-end:

- [ ] Step 1: Build passes
- [ ] Step 2: Read-only / query commands work
- [ ] Step 3: Dry-run or preview produces correct output
- [ ] Step 4: Full workflow succeeds
- [ ] Step 5: Cleanup / teardown leaves no artifacts

## 5. Code Review

- [ ] Code review performed following CodeReview.md guidelines
- [ ] Review logged with date, commit hash, findings, and proposed
      actions
- [ ] All high-severity findings resolved before release
- [ ] Medium-severity findings either resolved or explicitly deferred
      with rationale in TODO.md

## 6. User Stories and TODO

- [ ] USER_STORIES.md: completed stories match implemented code
- [ ] USER_STORIES.md: no story marked Completed with unmet acceptance
      criteria
- [ ] TODO.md: all `[x]` items correspond to implemented code
- [ ] TODO.md: all `[ ]` items correspond to unimplemented work
- [ ] TODO.md: no stale file references or architecture descriptions
- [ ] Items requiring human review are flagged and documented

## 7. Urgent Fixes

- [ ] No known bugs with severity High or above
- [ ] All code review findings marked as urgent are resolved
- [ ] No regressions from previous release (compare test results)

## 8. Documentation

- [ ] README.md: accurate, reflects current architecture and workflow
- [ ] ARCHITECTURE.md: module table matches current source files
- [ ] CLAUDE.md: development rules current and accurate
- [ ] CodeReview.md: review guidelines and refactoring catalog current
- [ ] TestPlan.md: test plans match current behavior

## 9. Git Hygiene

- [ ] Local main and origin/main are in sync
- [ ] No uncommitted changes
- [ ] Feature branches merged or explicitly deferred
- [ ] Tag created on main after all criteria are met
- [ ] Tag pushed to origin

## 10. Architecture Quality (Lakos / Booch / Gamma / Martin)

- [ ] No new technical debt introduced without explicit classification
      (deliberate/prudent) and TODO entry. Debt ledger balance reviewed:
      are we paying down more than accumulating?
- [ ] Coupling audit: no module gained excessive new dependencies since
      last release without justification
- [ ] Cohesion check: every new or modified source file can be named in
      one phrase. If you struggle to name it, it needs splitting.
      (Booch: maximal cohesion)
- [ ] Data model review: no struct has grown fields unused for the
      majority of its instances (Booch: data bags are a smell)
- [ ] Component cohesion: each module satisfies REP (independently
      releasable), CCP (changes together), and CRP (no forced
      dependencies) (Martin)
- [ ] Component coupling: dependency graph is acyclic (ADP), dependencies
      point toward stability (SDP) (Martin)
- [ ] Design patterns applied correctly: new pattern usage reviewed for
      appropriateness — use because the code needs it, not because we can
      (Gamma)

## 11. Pipeline Readiness (Humble + Farley)

- [ ] CI pipeline passes on the release commit
- [ ] All pipeline stages automated — no manual steps required
- [ ] A new contributor can clone, build, and run the tests by following
      only the documentation — no oral tradition, no undocumented steps
- [ ] Release artifacts are reproducible from the tagged commit

## 12. Hyrum's Law Check (Winters et al.)

- [ ] No internal implementation details leaked into the public API
      since last release
- [ ] Any observable behavior change is intentional and documented in
      the changelog

## 13. Test Coverage (non-blocking)

New features may ship as alpha or technology preview without full test
coverage. Mark them as such in the release notes. This section is
aspirational — it does not block a release.

- [ ] All changes since last release have been verified by at least one
      automated test (unit or integration)
- [ ] New features without tests are marked "alpha" or "technology
      preview" in the release notes

## Release Process

1. Verify all criteria above are checked (section 13 non-blocking)
2. Tag on main: `git tag -a vX.Y.Z -m "{{PROJECT_NAME}} X.Y.Z — summary"`
3. Push: `git push origin main --tags`
4. Update project tracking if state changed significantly
