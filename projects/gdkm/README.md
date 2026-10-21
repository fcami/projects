# gdkm — GitHub deploy-key manager

Move GitHub deploy keys between repositories with one command. GitHub allows a
public key to be a deploy key on only one repository, so reusing a key means
removing it from the old repo first; this tool does that, rolls back if the add
fails, and records where each key is in a TOML config. See `USER_STORIES.md` for the spec.

One file, `src/gdkm.py`; Python 3, stdlib plus `python3-tomlkit`.

## Authentication

The tool runs `gh auth token` once per run, lazily (not for `--dry-run`, `init`
or anything that makes no GitHub call), then talks to `https://api.github.com`
with `urllib`. It honours `GH_TOKEN` / `GITHUB_TOKEN` like `gh` does, and never
stores, prints or logs the token.

- Classic token: `repo` scope (`gh auth refresh -h github.com -s repo`).
- Fine-grained token: "Administration: read and write" on the repos.
- Organisation repos behind SAML SSO: authorize the token for that org.

## Usage

    gdkm --key laptop --repo foo            # read-only on <github_user>/foo
    gdkm --key laptop --repo org/bar --rw   # move, read-write
    gdkm --key laptop --detach
    gdkm status
    gdkm init --user fcami
    gdkm init --from-github [--user fcami] [--org some-org ...]
    gdkm import [--org some-org ...]
    gdkm repos add foo some-org/bar
    gdkm repos remove foo
    gdkm repos list
    gdkm --key laptop --repo foo --dry-run

(Run `./src/gdkm.py ...` directly, or symlink it as `gdkm`.)
`--config PATH` overrides `$XDG_CONFIG_HOME/gdkm/config.toml`
(`~/.config/...`). Exit status is 0 on success or no-op, 1 on errors, 2 on usage errors.

Behaviour notes:

- The key's real location is checked on GitHub before acting; keys are matched by
  type plus base64 blob (comment and title ignored). Drift is warned about.
- Order: delete from the current repo, add to the target, roll back on failure,
  and only then update the config (atomic write, comments and mode preserved).
- `--dry-run` on attach, detach and `repos` reads the config only: it trusts
  the recorded state, makes no GitHub call and needs no token. On
  `init --from-github` and `import` it still scans GitHub (read-only, so it
  needs the token) but writes nothing.

## Bootstrapping from GitHub

`init --from-github` creates a config from the deploy keys already on GitHub;
`import` merges them into an existing one. Private keys are never involved:
GitHub only returns public keys, so `pubkey` is stored as `type blob` (no
comment).

- `--org NAME` (repeatable; `--org=NAME` works too) picks whose repos are
  scanned; the default is `github_user`. For the logged-in user the scan uses
  `GET /user/repos?affiliation=owner` (private repos included); any other name
  uses `GET /orgs/NAME/repos?type=all`, and an unknown org is an error.
- Repos whose keys can't be listed (403/404, not an admin) are skipped and
  counted in the summary. Every deploy key found is imported.
- Nicknames come from the key title, lowercased, with anything outside
  `[a-z0-9_-]` turned into `-` (empty title: `key`). On a clash the repo name is
  appended (`deploy-foo`), then a number (`deploy-foo-2`).
- `repos` gets only repos that have at least one key. Archived repos are
  imported with an `# archived` comment on the key's `repo` line and a warning.
- `init --from-github` takes `github_user` from `--user`, else from the
  logged-in account, and refuses to overwrite an existing config.
- `import` keeps the nickname and pubkey line of keys already in the config,
  corrects `repo`/`mode` (`fixed`), adds new keys (`added`) and leaves keys the
  scan didn't see untouched (`not found in scan`).

## Managing the repo list

`repos add NAME...` checks that each repo exists and that you can list its
deploy keys (admin) before adding it; nothing is added if any check fails.
`repos remove NAME...` refuses while a key is recorded on the repo, naming the
key. `repos list` shows each repo with the keys recorded on it.

## Config

See `example-config.toml` (the same format as in `USER_STORIES.md`).

## Development

    make test        # unit tests (python3 -m unittest)
    make lint        # black --check, flake8, pylint
    make fmt         # apply black

Tests use an in-memory fake GitHub and a fake token provider; they never touch
the network or the real `gh`. Dependencies are Fedora/Debian packages only
(`python3-tomlkit`, `black`, `flake8`, `pylint`); nothing comes from PyPI.

## Packaging

`gdkm.spec` builds a noarch Fedora RPM (the tests run in `%check`). Its source
tarball comes from committed content only, so commit first:

    make release                        # writes gdkm-<version>.tar.gz
    rpmbuild -bs --define "_sourcedir $PWD" gdkm.spec

`<version>` is read from `gdkm.spec`; `make clean` removes the tarball.

## Origin

Imported from a local, unpublished `github-tools` repository; its git history
was not preserved.

## License

See [LICENSE](LICENSE).
