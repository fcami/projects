# gdkm — User Stories

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

All stories below, US-1 to US-17, are implemented and their acceptance
criteria are covered by the tests in `tests/`. They were written before
the move into this monorepo and are kept verbatim, except that the
command and its config directory were renamed from `deploy-key-manager`
to `gdkm` (approved by the maintainer).

### Context

A GitHub deploy key (a public SSH key) can be attached to **at most one
repository on all of GitHub**. Reusing a key means detaching it from its current
repo first. `gdkm` moves a named key to a target repo in one
command and keeps track of where each key is in a single config file.

Decisions:

- Language: Python 3, stdlib + Fedora packages only (`python3-tomlkit`); no PyPI.
- GitHub access: the tool gets a token by running `gh auth token` once per run
  and calls the GitHub REST API with Python's stdlib (`urllib`). It never saves,
  prints or logs the token.
- Managed repos: one global list, shared by all keys; a repo used with `--repo`
  is added to it automatically.
- `github_user` is the default owner: `--repo foo` means `<github_user>/foo`,
  and `--repo org/foo` is used as-is.

### Config file

Default path: `$XDG_CONFIG_HOME/gdkm/config.toml`
(`~/.config/...`), overridable with `--config PATH`.

```toml
# Hand-edited parts: github_user, keys.*.pubkey. The tool maintains the rest.
github_user = "fcami"

# Repositories this tool manages (auto-extended on use).
repos = ["fcami/foo", "some-org/bar"]

[keys.laptop]
pubkey = "ssh-ed25519 AAAAC3Nza... laptop@example"
repo = "fcami/foo"   # where the key is attached now ("" = attached nowhere)
mode = "ro"          # "ro" or "rw"

[keys.ci]
pubkey = "ssh-ed25519 AAAAC3Nza... ci@example"
repo = ""
mode = "ro"
```

### Core stories

#### US-1 — Attach a key read-only
As a maintainer, I want to run
`gdkm --repo foo --key laptop`
so that the `laptop` key becomes a **read-only** deploy key on `fcami/foo`.

- The key is created on GitHub with title `laptop` and `read_only: true`.
- In the config, `keys.laptop.repo` becomes `fcami/foo` and `mode` becomes `ro`.
- The command prints one line saying what changed (e.g. `laptop: (none) -> fcami/foo [ro]`).

#### US-2 — Attach a key read-write
As a maintainer, I want to add `--rw` to the same command so the key is attached
with write access.

- Without `--rw` the key is always read-only. Nothing else turns on write access.
- The config records `mode = "rw"`.

#### US-3 — Move a key between repos
As a maintainer, I want to run the command with a new `--repo` so the key is
removed from the repo it is on now and attached to the new one.

- The key is removed from the old repo **before** it is added to the new one,
  because GitHub refuses a key that is already in use.
- The config's `repo` is updated only after the add succeeds.
- Output shows both ends: `laptop: fcami/foo [ro] -> some-org/bar [rw]`.

#### US-4 — Change mode on the same repo
As a maintainer, I want to re-run the command on the repo the key is already on,
with or without `--rw`, to switch between ro and rw.

- GitHub can't edit a deploy key, so the tool removes it and adds it again.
- If the key is already on that repo with the requested mode, nothing changes
  and the tool reports `already attached`. It exits 0.

#### US-5 — Short and full repo names
As a maintainer, I want `--repo foo` to mean `<github_user>/foo` and
`--repo org/foo` to be used unchanged, so I can manage personal and org repos.

- Names are saved in the config in their full `owner/name` form.

#### US-6 — Managed repo list grows on use
As a maintainer, I want a repo I target to be added to `repos` automatically,
so I don't have to edit the config beforehand.

- The repo is added only after the attach succeeds, so a typo isn't recorded.
- No duplicates. The existing order is kept and new repos go at the end.

#### US-7 — Failure doesn't strand the key
As a maintainer, if adding the key to the target repo fails (no admin rights,
repo doesn't exist, network error), I want the key put back where it was.

- The tool re-adds the key to the previous repo with the previous mode.
- The config is left unchanged.
- The exit code is non-zero and the error says what failed and whether the
  rollback worked. If the rollback also failed, the error says the key is now
  attached nowhere.

#### US-8 — Trust GitHub, not just the config
As a maintainer, I want the tool to check where the key really is before it
acts, because someone may have changed things in the web UI.

- Keys are matched by key type plus base64 blob. The trailing comment and the
  title on GitHub are ignored.
- If the key is no longer on the repo the config names, the tool warns and
  goes on without trying to remove it.
- If GitHub answers "key is already in use" when adding, the tool searches every
  repo in `repos` for the key. If it finds it, it removes it there and tries the
  add again. If not, it reports that the key is in use on a repo it doesn't
  manage.

#### US-9 — Config edits are safe
As a maintainer, I want the tool to keep my comments and layout when it saves
the config, and never leave a half-written file.

- The file is written to a temporary file in the same directory, `fsync`ed,
  then renamed over the original. Its permissions are kept.
- Comments and key order are kept (tomlkit).

#### US-10 — Clear errors for bad input
As a maintainer, I want clear messages when:

- `--key` names a nickname that isn't in the config. The message lists the known nicknames.
- The config is missing or isn't valid TOML, or a key has no `pubkey`.
- `pubkey` isn't a valid OpenSSH public key line.
- `gh` isn't installed, or `gh auth token` fails (not logged in). The message
  says to run `gh auth login`.
- GitHub rejects the token (401) or the token lacks rights (403/404). The
  message suggests `gh auth refresh -h github.com -s repo`.

### Secondary stories

#### US-11 — Status
As a maintainer, I want `gdkm status` to list each key with its
nickname, recorded repo, mode, and whether GitHub agrees with the config
(`ok` / `missing` / `mode differs`).

#### US-12 — Detach
As a maintainer, I want `gdkm --key laptop --detach` to remove the
key from its repo and set `repo = ""`.

#### US-13 — Dry run
As a maintainer, I want `--dry-run` to print the GitHub calls the tool would
make and the config change, without doing either.

#### US-14 — Create a starter config
As a new user, I want `gdkm init --user fcami` to write a
commented starter config. It must refuse to overwrite an existing one.

### Bootstrapping from GitHub

GitHub's API returns each deploy key's public key (without its comment),
title, `read_only` flag and id, for repos where the token has admin rights.
Private keys are never on GitHub. A key can be on only one repo, so a scan maps
each key found to exactly one repo and mode.

Shared scan rules (US-15, US-16):

- `--org NAME` (repeatable, `--org=NAME` also accepted) selects whose repos are
  scanned. With no `--org`, the scan covers `github_user`.
- If NAME is the logged-in user (`GET /user`), the scan lists
  `GET /user/repos?affiliation=owner`, which includes private repos. Any other
  NAME is listed with `GET /orgs/NAME/repos?type=all`. An unknown org is an
  error.
- For each repo it lists the deploy keys. Repos answering 403/404 (not an
  admin) are skipped quietly, and the summary gives how many were skipped.
- **Every** deploy key found is imported; there are no filters.
- Nicknames come from the key title: lowercased, with characters outside
  `[a-z0-9_-]` turned into `-`, and empty titles become `key`. On a clash the
  repo name is appended (`deploy-foo`), then a number (`deploy-foo-2`).
- `pubkey` is stored as `type blob`, since GitHub doesn't return the comment.
- `repos` gets only the repos that have at least one deploy key.
- Archived repos are imported, but each one gets a comment in the config and a
  warning in the summary, because GitHub won't let the tool change keys there.
- `--dry-run` prints what would be written and writes nothing.

#### US-15 — Build a new config from GitHub
As a new user, I want `gdkm init --from-github [--org NAME ...]`
to create my config from the deploy keys already on GitHub.

- `github_user` is taken from `--user` if given, otherwise from the logged-in
  account.
- The tool refuses to overwrite an existing config, as plain `init` does.
- The summary lists each key (nickname, repo, mode) and the number of repos
  scanned and skipped.

#### US-16 — Import into an existing config
As a maintainer, I want `gdkm import [--org NAME ...]` to merge
what GitHub reports into my existing config.

- A key already in the config (matched by type plus blob) keeps its nickname
  and pubkey line. Its `repo`/`mode` is corrected if GitHub disagrees, and the
  summary reports it as `fixed`.
- Unknown keys are added under new nicknames that don't clash with existing
  ones.
- Repos where keys were found are appended to `repos`, without duplicates.
- A config key that the scan didn't find is left unchanged and reported as
  `not found in scan`, because the scan may not have covered its repo.
- Comments are preserved and the file is saved safely (US-9).

### Managing the repo list

#### US-17 — Add, remove and list managed repos
As a maintainer, I want to manage `repos` without attaching a key:

- `gdkm repos add NAME...` uses the same short/full name rules
  (US-5). It checks that each repo exists and that I'm an admin (it can list
  the repo's deploy keys) before adding it. Duplicates are ignored.
- `gdkm repos remove NAME...` refuses to remove a repo that a key
  is recorded on, and names that key.
- `gdkm repos list` prints each repo with the nicknames of the
  keys recorded on it.
- `--dry-run` works for `add` and `remove`.

### Implementation requirements

- One Python file, `gdkm.py`, that can be run directly.
- A standard object-oriented design: value objects for keys and repos, a config
  class, a `gh` client class, a class holding the attach/move logic, and the CLI.
- Passes `black --check`, `flake8` (max line length 88) and `pylint` with no
  warnings.
- Tests run against a fake GitHub API and a fake `gh auth token`; they never
  touch the network or the real `gh`.

### Out of scope

- Generating SSH key pairs, or handling private keys at all.
- User-level SSH keys (`/user/keys`). Only deploy keys are handled.
- More than one GitHub host or account.
- Installing from PyPI.

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
