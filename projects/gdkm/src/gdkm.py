#!/usr/bin/env python3
"""gdkm: move GitHub deploy keys between repos with one command.

A deploy key can be attached to at most one repository on all of GitHub. This
tool moves a named key to a target repository and records where each key is in
a single TOML config file; it can also build or refresh that file from the
deploy keys already on GitHub and manage the list of repos. The GitHub token
comes from ``gh auth token`` and is used only in memory, for calls to the
GitHub REST API.
"""

# The project is deliberately a single file (see US.md), hence its length.
# pylint: disable=too-many-lines

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterator, Optional

import tomlkit

KEY_TYPES = frozenset(
    {
        "ssh-ed25519",
        "ssh-rsa",
        "ssh-dss",
        "ecdsa-sha2-nistp256",
        "ecdsa-sha2-nistp384",
        "ecdsa-sha2-nistp521",
        "sk-ssh-ed25519@openssh.com",
        "sk-ecdsa-sha2-nistp256@openssh.com",
    }
)
API_URL = "https://api.github.com"
API_VERSION = "2022-11-28"
TIMEOUT = 30.0
MODES = ("ro", "rw")
OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$")
NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")

ARCHIVED_NOTE = "archived: GitHub will not let this tool change keys here"

STARTER_CONFIG = """\
# gdkm configuration.
# Hand-edited parts: github_user, keys.*.pubkey. The tool maintains the rest.
github_user = "{user}"

# Repositories this tool manages (auto-extended on use).
repos = []

# One table per key. Add the PUBLIC key line (never a private key):
#
# [keys.laptop]
# pubkey = "ssh-ed25519 AAAAC3Nza... laptop@example"
# repo = ""     # where the key is attached now ("" = attached nowhere)
# mode = "ro"   # "ro" or "rw"
"""


class DeployKeyManagerError(Exception):
    """Base class for all errors reported to the user."""


class ConfigError(DeployKeyManagerError):
    """The config file is missing, unreadable or invalid."""


class InvalidInputError(DeployKeyManagerError):
    """A user-supplied key or repository name is malformed."""


class GitHubError(DeployKeyManagerError):
    """A GitHub API call failed."""


class GitHubAuthError(GitHubError):
    """No usable token, or GitHub rejected it."""


class GitHubNetworkError(GitHubError):
    """The request never got an HTTP answer (DNS, connection, timeout)."""


class GitHubNotFoundError(GitHubError):
    """404: no such resource, or no access to it."""


class GitHubForbiddenError(GitHubError):
    """403: the token lacks the rights for this call."""


class GitHubKeyInUseError(GitHubError):
    """422: the key is already a deploy key somewhere on GitHub."""


@dataclass(frozen=True)
class PublicKey:
    """An OpenSSH public key; equality ignores the trailing comment."""

    key_type: str
    blob: str
    line: str

    @classmethod
    def parse(cls, line: str) -> PublicKey:
        """Parse and validate a single OpenSSH public key line."""
        line = line.strip()
        parts = line.split()
        if len(parts) < 2 or "\n" in line:
            raise InvalidInputError(f"not an OpenSSH public key line: {line[:40]!r}")
        key_type, blob = parts[0], parts[1]
        if key_type not in KEY_TYPES:
            raise InvalidInputError(f"unsupported or unknown key type {key_type!r}")
        try:
            raw = base64.b64decode(blob, validate=True)
            (length,) = struct.unpack(">I", raw[:4])
            inner = raw[4 : 4 + length].decode("ascii")
        except (ValueError, struct.error) as err:
            raise InvalidInputError(
                "public key blob is not valid OpenSSH base64 data"
            ) from err
        if inner != key_type:
            raise InvalidInputError(f"public key blob does not match type {key_type!r}")
        return cls(key_type, blob, line)

    def same_key(self, other: PublicKey) -> bool:
        """Compare by type and blob only."""
        return (self.key_type, self.blob) == (other.key_type, other.blob)


@dataclass(frozen=True)
class Repo:
    """A GitHub repository as ``owner/name``."""

    owner: str
    name: str

    @classmethod
    def parse(cls, text: str, default_owner: str = "") -> Repo:
        """Normalize ``name`` (using default_owner) or ``owner/name``."""
        owner, sep, name = text.partition("/")
        if not sep:
            owner, name = default_owner, text
            if not owner:
                raise InvalidInputError(
                    f"short repo name {text!r} needs github_user in the config"
                )
        if not OWNER_RE.match(owner) or not NAME_RE.match(name) or name in (".", ".."):
            raise InvalidInputError(
                f"malformed repository name {text!r} (want 'name' or 'owner/name')"
            )
        return cls(owner, name)

    def __str__(self) -> str:
        return f"{self.owner}/{self.name}"


@dataclass(frozen=True)
class RemoteKey:
    """A deploy key as GitHub reports it."""

    key_id: int
    key: Optional[PublicKey]
    read_only: bool
    title: str = ""

    @property
    def mode(self) -> str:
        """``ro`` or ``rw``."""
        return "ro" if self.read_only else "rw"


@dataclass(frozen=True)
class Placement:
    """Where a key is attached, and how."""

    repo: Repo
    mode: str

    def __str__(self) -> str:
        return f"{self.repo} [{self.mode}]"


@dataclass
class KeyEntry:
    """One ``[keys.NICK]`` table of the config."""

    nick: str
    pubkey: PublicKey
    repo: Optional[Repo]
    mode: str


@dataclass(frozen=True)
class RepoInfo:
    """A repository as listed by GitHub."""

    repo: Repo
    archived: bool


@dataclass(frozen=True)
class ScannedKey:
    """A deploy key found on GitHub during a scan."""

    title: str
    pubkey: PublicKey
    repo: Repo
    mode: str
    archived: bool


@dataclass
class ScanResult:
    """Everything a scan found, plus how many repos it covered or skipped."""

    keys: list[ScannedKey]
    scanned: int
    skipped: int


class Config:
    """The TOML config file, read and written with tomlkit."""

    def __init__(self, path: str, text: Optional[str] = None) -> None:
        """Load ``path``, or parse ``text`` as if it were the file's content."""
        self.path = path
        self._doc = self._parse(path, self._read(path) if text is None else text)
        user = self._doc.get("github_user", "")
        if not isinstance(user, str):
            raise ConfigError("config: github_user must be a string")
        self.github_user: str = user
        try:
            self.repos: list[Repo] = [
                Repo.parse(str(r), user) for r in self._doc.get("repos", [])
            ]
            self.keys: dict[str, KeyEntry] = {
                nick: self._entry(nick, table)
                for nick, table in self._doc.get("keys", {}).items()
            }
        except InvalidInputError as err:
            raise ConfigError(f"config {path}: {err}") from err

    @staticmethod
    def _read(path: str) -> str:
        try:
            with open(path, encoding="utf-8") as handle:
                text = handle.read()
        except FileNotFoundError as err:
            raise ConfigError(
                f"config file {path} not found "
                "(create one with `gdkm init --user USER`)"
            ) from err
        except OSError as err:
            raise ConfigError(f"cannot read config {path}: {err}") from err
        return text

    @staticmethod
    def _parse(path: str, text: str):
        try:
            return tomlkit.parse(text)
        except tomlkit.exceptions.TOMLKitError as err:
            raise ConfigError(f"config {path} is not valid TOML: {err}") from err

    def _entry(self, nick: str, table) -> KeyEntry:
        if not isinstance(table, dict) or not table.get("pubkey"):
            raise ConfigError(f"config: key {nick!r} has no pubkey")
        try:
            pubkey = PublicKey.parse(str(table["pubkey"]))
        except InvalidInputError as err:
            raise ConfigError(f"config: key {nick!r}: {err}") from err
        mode = str(table.get("mode", "ro"))
        if mode not in MODES:
            raise ConfigError(f'config: key {nick!r}: mode must be "ro" or "rw"')
        repo_text = str(table.get("repo", "") or "")
        repo = Repo.parse(repo_text, self.github_user) if repo_text else None
        return KeyEntry(nick, pubkey, repo, mode)

    def key(self, nick: str) -> KeyEntry:
        """Return the entry for a nickname or raise listing known ones."""
        if nick not in self.keys:
            known = ", ".join(self.keys) or "(none)"
            raise DeployKeyManagerError(f"unknown key {nick!r}; known keys: {known}")
        return self.keys[nick]

    def set_placement(
        self, nick: str, repo: Optional[Repo], mode: str, archived: bool = False
    ) -> None:
        """Set a key's repo/mode in memory (extending ``repos``); no save.

        An archived repo gets an explanatory comment on the ``repo`` line.
        """
        table = self._doc["keys"][nick]
        table["repo"] = str(repo) if repo else ""
        table["mode"] = mode
        item = table["repo"]
        if archived:
            item.comment(ARCHIVED_NOTE)
        elif item.trivia.comment.lstrip("# ").startswith("archived"):
            item.comment("")
        entry = self.keys[nick]
        entry.repo, entry.mode = repo, mode
        if repo:
            self.add_repo(repo)

    def record(self, nick: str, repo: Optional[Repo], mode: str) -> None:
        """Update a key's repo/mode (extending ``repos``) and save atomically."""
        self.set_placement(nick, repo, mode)
        self.save()

    def add_key(self, nick: str, found: ScannedKey) -> None:
        """Add a ``[keys.NICK]`` table (stored as ``type blob``); no save."""
        pubkey, mode = found.pubkey, found.mode
        table = tomlkit.table()
        table["pubkey"] = f"{pubkey.key_type} {pubkey.blob}"
        table["repo"] = ""
        table["mode"] = mode
        if "keys" not in self._doc:
            self._doc["keys"] = tomlkit.table(is_super_table=True)
        self._doc["keys"][nick] = table
        self.keys[nick] = KeyEntry(
            nick,
            PublicKey(pubkey.key_type, pubkey.blob, str(table["pubkey"])),
            None,
            mode,
        )
        self.set_placement(nick, found.repo, mode, found.archived)

    def add_repo(self, repo: Repo) -> bool:
        """Append a repo to ``repos`` unless present; no save. True if added."""
        if repo in self.repos:
            return False
        if "repos" not in self._doc:
            self._doc["repos"] = []
        self._doc["repos"].append(str(repo))
        self.repos.append(repo)
        return True

    def remove_repo(self, repo: Repo) -> None:
        """Remove a repo from ``repos``; no save."""
        index = self.repos.index(repo)
        del self._doc["repos"][index]
        del self.repos[index]

    def keys_on(self, repo: Repo) -> list[str]:
        """Nicknames of the keys recorded on a repo."""
        return [nick for nick, entry in self.keys.items() if entry.repo == repo]

    def save(self) -> None:
        """Write the config via tempfile + fsync + rename, keeping its mode."""
        path = os.path.realpath(self.path)
        try:
            mode = os.stat(path).st_mode & 0o7777
        except FileNotFoundError:
            mode = 0o644
        fd, tmp = tempfile.mkstemp(
            dir=os.path.dirname(path), prefix=".gdkm-", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(tomlkit.dumps(self._doc))
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(tmp, mode)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise

    @staticmethod
    def init(path: str, user: str) -> None:
        """Write a starter config; refuse to overwrite an existing file."""
        if not OWNER_RE.match(user):
            raise InvalidInputError(f"invalid GitHub user name {user!r}")
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(STARTER_CONFIG.format(user=user))
                handle.flush()
                os.fsync(handle.fileno())
        except FileExistsError as err:
            raise ConfigError(f"{path} already exists; refusing to overwrite") from err

    @staticmethod
    def default_path() -> str:
        """``$XDG_CONFIG_HOME/gdkm/config.toml`` or ``~/.config``."""
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
        return os.path.join(base, "gdkm", "config.toml")


@dataclass(frozen=True)
class HttpRequest:
    """A request handed to a transport."""

    method: str
    url: str
    headers: dict[str, str]
    body: Optional[bytes]
    timeout: float


@dataclass(frozen=True)
class HttpResponse:
    """What a transport returns for any HTTP status."""

    status: int
    headers: dict[str, str]
    body: bytes


# A transport is a one-method strategy object; a class keeps it injectable.
class UrllibTransport:  # pylint: disable=too-few-public-methods
    """Real HTTP transport built on urllib.request."""

    def request(self, req: HttpRequest) -> HttpResponse:
        """Send a request; HTTP error statuses are returned, not raised.

        Network failures propagate as OSError (URLError, timeouts).
        """
        http_req = urllib.request.Request(
            req.url, data=req.body, headers=req.headers, method=req.method
        )
        try:
            with urllib.request.urlopen(http_req, timeout=req.timeout) as resp:
                return HttpResponse(
                    resp.status,
                    {k.lower(): v for k, v in resp.headers.items()},
                    resp.read(),
                )
        except urllib.error.HTTPError as err:
            return HttpResponse(
                err.code, {k.lower(): v for k, v in err.headers.items()}, err.read()
            )


# Callable strategy object, injectable in place of a plain function.
class GhTokenProvider:  # pylint: disable=too-few-public-methods
    """Obtains the GitHub token from `gh auth token` (honours GH_TOKEN)."""

    def __call__(self) -> str:
        """Run `gh auth token` and return its output."""
        if not shutil.which("gh"):
            raise GitHubAuthError(
                "the `gh` CLI is not installed (https://cli.github.com/)"
            )
        try:
            proc = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, check=False
            )
        except OSError as err:
            raise GitHubAuthError(f"cannot run gh: {err}") from err
        token = proc.stdout.strip()
        if proc.returncode != 0 or not token:
            raise GitHubAuthError("no GitHub token from gh; run `gh auth login`")
        return token


class GitHubClient:
    """Deploy-key operations against the GitHub REST API.

    The token comes from ``token_provider`` and is fetched once, lazily, on the
    first real request. It is never printed, logged or included in errors.
    """

    def __init__(
        self,
        token_provider: Optional[Callable[[], str]] = None,
        transport: Optional[UrllibTransport] = None,
    ) -> None:
        self._token_provider = token_provider or GhTokenProvider()
        self._transport = transport or UrllibTransport()
        self._token: Optional[str] = None

    def __repr__(self) -> str:
        return "GitHubClient()"

    def _headers(self, with_body: bool) -> dict[str, str]:
        if self._token is None:
            self._token = self._token_provider()
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "gdkm",
        }
        if with_body:
            headers["Content-Type"] = "application/json"
        return headers

    def _request(
        self, method: str, url: str, what: str, payload: Optional[dict] = None
    ) -> HttpResponse:
        if not url.startswith(API_URL + "/"):
            raise GitHubError(f"{what}: refusing to contact {url}")
        body = json.dumps(payload).encode() if payload is not None else None
        headers = self._headers(body is not None)
        try:
            resp = self._transport.request(
                HttpRequest(method, url, headers, body, TIMEOUT)
            )
        except OSError as err:
            raise GitHubNetworkError(f"{what}: network error: {err}") from err
        if resp.status >= 400:
            raise self._error(resp, what)
        return resp

    @staticmethod
    def _error(resp: HttpResponse, what: str) -> GitHubError:
        """Map an HTTP error response to one of our exceptions."""
        try:
            data = json.loads(resp.body)
            parts = [str(data.get("message", ""))]
            for item in data.get("errors", []):
                parts.append(
                    str(item.get("message", ""))
                    if isinstance(item, dict)
                    else str(item)
                )
        except (ValueError, AttributeError):
            parts = []
        text = "; ".join(p for p in parts if p) or "no details"
        if resp.status == 422 and "already in use" in text:
            return GitHubKeyInUseError(f"{what}: key is already in use")
        if resp.status == 401:
            return GitHubAuthError(
                f"{what}: token rejected (bad or expired); run `gh auth login` "
                "or `gh auth refresh -h github.com -s repo`"
            )
        if resp.status == 403:
            return GitHubForbiddenError(
                f"{what}: forbidden ({text}); the token needs the `repo` scope "
                "(classic) or Administration read/write (fine-grained), and "
                "SSO authorization for the org"
            )
        if resp.status == 404:
            return GitHubNotFoundError(
                f"{what}: not found (no such repo, or no admin rights on it)"
            )
        return GitHubError(f"{what}: HTTP {resp.status}: {text}")

    @staticmethod
    def _next_link(resp: HttpResponse) -> Optional[str]:
        for part in resp.headers.get("link", "").split(","):
            match = re.match(r'\s*<([^>]+)>\s*;\s*rel="next"', part)
            if match:
                return match.group(1)
        return None

    def _pages(self, url: str, what: str) -> Iterator[dict]:
        """Yield every item of a paginated list, following ``Link: rel=next``."""
        next_url: Optional[str] = url
        while next_url:
            resp = self._request("GET", next_url, what)
            try:
                items = json.loads(resp.body)
                yield from items
            except (ValueError, TypeError) as err:
                raise GitHubError(f"{what}: unexpected response from GitHub") from err
            next_url = self._next_link(resp)

    def list_keys(self, repo: Repo) -> list[RemoteKey]:
        """List all deploy keys of a repo, following pagination."""
        what = f"listing keys of {repo}"
        keys = []
        for item in self._pages(f"{API_URL}/repos/{repo}/keys?per_page=100", what):
            try:
                pub: Optional[PublicKey] = PublicKey.parse(item.get("key", ""))
            except InvalidInputError:
                pub = None
            try:
                keys.append(
                    RemoteKey(
                        item["id"],
                        pub,
                        bool(item.get("read_only", True)),
                        str(item.get("title", "")),
                    )
                )
            except (KeyError, AttributeError) as err:
                raise GitHubError(f"{what}: unexpected response from GitHub") from err
        return keys

    def current_user(self) -> str:
        """Return the login of the authenticated user."""
        resp = self._request("GET", f"{API_URL}/user", "getting the current user")
        try:
            return str(json.loads(resp.body)["login"])
        except (ValueError, TypeError, KeyError) as err:
            raise GitHubError("unexpected response from GET /user") from err

    def list_repos(self, owner: str, is_self: bool) -> list[RepoInfo]:
        """List the repos of the logged-in user (``is_self``) or of an org."""
        what = f"listing repos of {owner}"
        if is_self:
            url = f"{API_URL}/user/repos?affiliation=owner&per_page=100"
        else:
            url = f"{API_URL}/orgs/{owner}/repos?type=all&per_page=100"
        repos = []
        try:
            for item in self._pages(url, what):
                repos.append(
                    RepoInfo(Repo.parse(item["full_name"]), bool(item.get("archived")))
                )
        except GitHubNotFoundError as err:
            raise GitHubError(f"unknown organization {owner!r}") from err
        except (KeyError, TypeError, AttributeError, InvalidInputError) as err:
            raise GitHubError(f"{what}: unexpected response from GitHub") from err
        return repos

    def find_key(self, repo: Repo, pubkey: PublicKey) -> Optional[RemoteKey]:
        """Return the deploy key matching pubkey on repo, if any."""
        for remote in self.list_keys(repo):
            if remote.key and remote.key.same_key(pubkey):
                return remote
        return None

    def add_key(self, repo: Repo, title: str, pubkey: PublicKey, mode: str) -> None:
        """Add a deploy key (title, read-only unless mode is ``rw``)."""
        self._request(
            "POST",
            f"{API_URL}/repos/{repo}/keys",
            f"adding key to {repo}",
            {"title": title, "key": pubkey.line, "read_only": mode == "ro"},
        )

    def delete_key(self, repo: Repo, key_id: int) -> None:
        """Remove a deploy key by id."""
        self._request(
            "DELETE",
            f"{API_URL}/repos/{repo}/keys/{key_id}",
            f"removing key from {repo}",
        )


class KeyManager:
    """Attach, move, detach and report on deploy keys."""

    def __init__(
        self,
        config: Config,
        client: GitHubClient,
        dry_run: bool = False,
        out: Callable[[str], None] = print,
    ) -> None:
        self.config = config
        self.client = client
        self.dry_run = dry_run
        self.out = out

    @staticmethod
    def warn(message: str) -> None:
        """Print a warning to stderr."""
        print(f"warning: {message}", file=sys.stderr)

    @staticmethod
    def _fmt(placement: Optional[Placement]) -> str:
        return str(placement) if placement else "(none)"

    def _plan(self, text: str) -> None:
        self.out(f"would run: {text}")

    def _locate(self, entry: KeyEntry) -> Optional[tuple[Placement, int]]:
        """Find the key on GitHub on the repo the config names (US-8)."""
        if not entry.repo:
            return None
        remote = self.client.find_key(entry.repo, entry.pubkey)
        if not remote:
            self.warn(
                f"{entry.nick}: key not found on {entry.repo} "
                "(config out of date); continuing"
            )
            return None
        if remote.mode != entry.mode:
            self.warn(
                f"{entry.nick}: GitHub has it as {remote.mode} on {entry.repo}, "
                f"config says {entry.mode}"
            )
        return Placement(entry.repo, remote.mode), remote.key_id

    def attach(self, nick: str, repo_text: str, read_write: bool) -> None:
        """Attach (or move, or change the mode of) a key."""
        entry = self.config.key(nick)
        target = Placement(
            Repo.parse(repo_text, self.config.github_user), "rw" if read_write else "ro"
        )
        if self.dry_run:
            self._dry_attach(entry, target)
            return
        current = self._locate(entry)
        if current and current[0] == target:
            if (entry.repo, entry.mode) != (target.repo, target.mode) or (
                target.repo not in self.config.repos
            ):
                self.config.record(nick, target.repo, target.mode)
            self.out(f"{nick}: already attached to {target}")
            return
        previous = current[0] if current else None
        if current:
            self.client.delete_key(current[0].repo, current[1])
        try:
            previous = self._add_resolving_conflict(entry, target, previous)
        except GitHubError as err:
            self._rollback(entry, previous, err)
        self.config.record(nick, target.repo, target.mode)
        self.out(f"{nick}: {self._fmt(previous)} -> {target}")

    def _add_resolving_conflict(
        self, entry: KeyEntry, target: Placement, previous: Optional[Placement]
    ) -> Optional[Placement]:
        """Add the key; on "already in use" hunt it down in managed repos."""
        try:
            self.client.add_key(target.repo, entry.nick, entry.pubkey, target.mode)
            return previous
        except GitHubKeyInUseError:
            pass
        found = self._search_managed(entry, target.repo)
        if not found:
            raise GitHubError(
                "key is in use on a repo not managed by this tool (not in `repos`)"
            )
        self.warn(f"{entry.nick}: key was actually on {found[0]}; removing it there")
        self.client.delete_key(found[0].repo, found[1])
        previous = previous or found[0]
        self.client.add_key(target.repo, entry.nick, entry.pubkey, target.mode)
        return previous

    def _search_managed(
        self, entry: KeyEntry, target: Repo
    ) -> Optional[tuple[Placement, int]]:
        """Look for the key on every managed repo, plus the target."""
        extra = [] if target in self.config.repos else [target]
        for repo in self.config.repos + extra:
            try:
                remote = self.client.find_key(repo, entry.pubkey)
            except GitHubError as err:
                self.warn(f"cannot search {repo}: {err}")
                continue
            if remote:
                return Placement(repo, remote.mode), remote.key_id
        return None

    def _rollback(
        self, entry: KeyEntry, previous: Optional[Placement], err: GitHubError
    ) -> None:
        """Restore the key where it was, then raise the original failure."""
        nick = entry.nick
        if not previous:
            raise DeployKeyManagerError(
                f"{nick}: {err} (key was not attached anywhere; "
                "nothing to roll back; config unchanged)"
            ) from err
        try:
            self.client.add_key(previous.repo, nick, entry.pubkey, previous.mode)
        except GitHubError as err2:
            raise DeployKeyManagerError(
                f"{nick}: {err}; rollback to {previous} FAILED ({err2}): "
                "the key is now attached NOWHERE; config unchanged"
            ) from err2
        raise DeployKeyManagerError(
            f"{nick}: {err}; rolled back to {previous}; config unchanged"
        ) from err

    def _dry_attach(self, entry: KeyEntry, target: Placement) -> None:
        nick = entry.nick
        recorded = Placement(entry.repo, entry.mode) if entry.repo else None
        if recorded == target:
            self.out(f"{nick}: already attached to {target} (per config)")
            return
        if entry.repo:
            self._plan(f"DELETE /repos/{entry.repo}/keys/<id of {nick}>")
        flag = "true" if target.mode == "ro" else "false"
        self._plan(
            f"POST /repos/{target.repo}/keys title={nick} key=<pubkey> "
            f"read_only={flag}"
        )
        extra = "" if target.repo in self.config.repos else "; append to repos"
        self._plan(
            f'config: keys.{nick}.repo = "{target.repo}", mode = "{target.mode}"{extra}'
        )
        self.out(f"{nick}: {self._fmt(recorded)} -> {target} (dry run)")

    def detach(self, nick: str) -> None:
        """Remove the key from its repo and record it as attached nowhere."""
        entry = self.config.key(nick)
        if self.dry_run:
            if entry.repo:
                self._plan(f"DELETE /repos/{entry.repo}/keys/<id of {nick}>")
            self._plan(f'config: keys.{nick}.repo = ""')
            return
        if not entry.repo:
            self.out(f"{nick}: not attached")
            return
        old = Placement(entry.repo, entry.mode)
        current = self._locate(entry)
        if current:
            self.client.delete_key(current[0].repo, current[1])
            old = current[0]
        self.config.record(nick, None, entry.mode)
        self.out(f"{nick}: {old} -> (none)")

    def status(self) -> int:
        """Print config-vs-GitHub state of every key; 1 if any lookup failed."""
        rows = [("KEY", "REPO", "MODE", "STATE")]
        cache: dict[Repo, list[RemoteKey]] = {}
        failed = False
        for nick, entry in self.config.keys.items():
            if not entry.repo:
                rows.append((nick, "-", entry.mode, "unattached"))
                continue
            try:
                if entry.repo not in cache:
                    cache[entry.repo] = self.client.list_keys(entry.repo)
            except GitHubAuthError:
                raise
            except GitHubError as err:
                rows.append((nick, str(entry.repo), entry.mode, f"error: {err}"))
                failed = True
                continue
            match = [
                r for r in cache[entry.repo] if r.key and r.key.same_key(entry.pubkey)
            ]
            if not match:
                state = "missing"
            elif match[0].mode != entry.mode:
                state = "mode differs"
            else:
                state = "ok"
            rows.append((nick, str(entry.repo), entry.mode, state))
        widths = [max(len(row[i]) for row in rows) for i in range(3)]
        for row in rows:
            cells = [cell.ljust(widths[i]) for i, cell in enumerate(row[:3])]
            self.out("  ".join(cells + [row[3]]))
        return 1 if failed else 0


class GitHubScanner:
    """Finds every deploy key on the repos of a user and/or organizations."""

    def __init__(self, client: GitHubClient) -> None:
        self.client = client
        self._login: Optional[str] = None

    def login(self) -> str:
        """The logged-in account (one ``GET /user`` per scanner)."""
        if self._login is None:
            self._login = self.client.current_user()
        return self._login

    def scan(self, owners: list[str]) -> ScanResult:
        """List the deploy keys of all repos of ``owners``.

        Repos whose keys answer 403/404 (no admin rights) are counted as
        skipped; any other error aborts the scan.
        """
        found: list[ScannedKey] = []
        seen: set[Repo] = set()
        scanned = skipped = 0
        for owner in owners:
            is_self = owner.lower() == self.login().lower()
            for info in self.client.list_repos(owner, is_self):
                if info.repo in seen:
                    continue
                seen.add(info.repo)
                try:
                    remotes = self.client.list_keys(info.repo)
                except (GitHubForbiddenError, GitHubNotFoundError):
                    skipped += 1
                    continue
                scanned += 1
                found.extend(
                    ScannedKey(r.title, r.key, info.repo, r.mode, info.archived)
                    for r in remotes
                    if r.key
                )
        return ScanResult(found, scanned, skipped)


@dataclass
class MergeLine:
    """One key in a merge summary."""

    nick: str
    repo: Optional[Repo]
    mode: str
    status: str


@dataclass
class MergeReport:
    """What a merge did, ready to print."""

    lines: list[MergeLine]
    archived: list[Repo]
    scanned: int
    skipped: int

    def render(self) -> list[str]:
        """Summary lines: one per key, counts, then archived-repo warnings."""
        rows = [(m.nick, str(m.repo or "-"), m.mode, m.status) for m in self.lines] or [
            ("(no keys)", "", "", "")
        ]
        widths = [max(len(row[i]) for row in rows) for i in range(3)]
        out = [
            "  ".join([c.ljust(widths[i]) for i, c in enumerate(row[:3])] + [row[3]])
            for row in rows
        ]
        out.append(
            f"scanned {self.scanned} repos, skipped {self.skipped} " "(no admin access)"
        )
        out.extend(
            f"warning: {repo} is archived; GitHub will not let this tool change "
            "keys there"
            for repo in self.archived
        )
        return out


class ConfigMerger:
    """Merges a scan of GitHub into a Config (in memory; the caller saves)."""

    def __init__(self, config: Config) -> None:
        self.config = config

    @staticmethod
    def _slug(text: str) -> str:
        return re.sub(r"[^a-z0-9_-]", "-", text.lower())

    def nickname(self, title: str, repo: Repo) -> str:
        """Derive a free nickname from a key title (then repo name, then number)."""
        base = self._slug(title) or "key"
        with_repo = f"{base}-{self._slug(repo.name)}"
        if base not in self.config.keys:
            return base
        if with_repo not in self.config.keys:
            return with_repo
        number = 2
        while f"{with_repo}-{number}" in self.config.keys:
            number += 1
        return f"{with_repo}-{number}"

    def merge(self, scan: ScanResult) -> MergeReport:
        """Apply a scan: add unknown keys, fix known ones, report the rest."""
        by_blob = {
            (e.pubkey.key_type, e.pubkey.blob): e for e in self.config.keys.values()
        }
        lines: list[MergeLine] = []
        archived: list[Repo] = []
        handled: set[str] = set()
        for found in scan.keys:
            entry = by_blob.get((found.pubkey.key_type, found.pubkey.blob))
            if entry is None:
                nick = self.nickname(found.title, found.repo)
                self.config.add_key(nick, found)
                status = "added"
            else:
                nick = entry.nick
                changed = (entry.repo, entry.mode) != (found.repo, found.mode)
                if changed or found.archived:
                    self.config.set_placement(
                        nick, found.repo, found.mode, found.archived
                    )
                status = "fixed" if changed else "unchanged"
            handled.add(nick)
            self.config.add_repo(found.repo)
            if found.archived and found.repo not in archived:
                archived.append(found.repo)
            lines.append(MergeLine(nick, found.repo, found.mode, status))
        lines.extend(
            MergeLine(nick, entry.repo, entry.mode, "not found in scan")
            for nick, entry in self.config.keys.items()
            if nick not in handled
        )
        return MergeReport(lines, archived, scan.scanned, scan.skipped)


class RepoList:
    """The ``repos`` subcommands: add, remove and list managed repos."""

    def __init__(
        self,
        config: Config,
        client: GitHubClient,
        dry_run: bool = False,
        out: Callable[[str], None] = print,
    ) -> None:
        self.config = config
        self.client = client
        self.dry_run = dry_run
        self.out = out

    def _parse(self, names: list[str]) -> list[Repo]:
        repos = [Repo.parse(n, self.config.github_user) for n in names]
        return list(dict.fromkeys(repos))

    def add(self, names: list[str]) -> None:
        """Add repos after checking each exists and lists its deploy keys."""
        todo = []
        for repo in self._parse(names):
            if repo in self.config.repos:
                self.out(f"{repo}: already managed")
            else:
                todo.append(repo)
        for repo in todo:
            if self.dry_run:
                self.out(f"would run: GET /repos/{repo}/keys (admin check)")
                self.out(f"would add {repo} to repos")
                continue
            try:
                self.client.list_keys(repo)
            except GitHubAuthError:
                raise
            except GitHubError as err:
                raise DeployKeyManagerError(
                    f"cannot add {repo}: {err} (needs an existing repo "
                    "where you are admin); config unchanged"
                ) from err
        if todo and not self.dry_run:
            for repo in todo:
                self.config.add_repo(repo)
                self.out(f"{repo}: added")
            self.config.save()

    def remove(self, names: list[str]) -> None:
        """Remove repos, refusing while a key is recorded on one of them."""
        todo = []
        for repo in self._parse(names):
            if repo not in self.config.repos:
                self.out(f"{repo}: not in repos")
                continue
            nicks = self.config.keys_on(repo)
            if nicks:
                raise DeployKeyManagerError(
                    f"cannot remove {repo}: key {', '.join(map(repr, nicks))} is "
                    "recorded on it; detach or move the key first"
                )
            todo.append(repo)
        for repo in todo:
            if self.dry_run:
                self.out(f"would remove {repo} from repos")
            else:
                self.config.remove_repo(repo)
                self.out(f"{repo}: removed")
        if todo and not self.dry_run:
            self.config.save()

    def show(self) -> None:
        """Print each managed repo with the keys recorded on it."""
        width = max((len(str(r)) for r in self.config.repos), default=0)
        for repo in self.config.repos:
            nicks = ", ".join(self.config.keys_on(repo)) or "-"
            self.out(f"{str(repo).ljust(width)}  {nicks}")


class Cli:
    """Command-line front end."""

    def __init__(self, client: Optional[GitHubClient] = None) -> None:
        self.client = client or GitHubClient()
        self.parser = self.build_parser()

    @staticmethod
    def build_parser() -> argparse.ArgumentParser:
        """Build the argparse parser: flat options plus subcommands."""
        common = argparse.ArgumentParser(add_help=False)
        common.add_argument(
            "--config",
            metavar="PATH",
            default=argparse.SUPPRESS,
            help=f"config file (default: {Config.default_path()})",
        )
        common.add_argument(
            "--dry-run",
            action="store_true",
            default=argparse.SUPPRESS,
            help="show what would be done without doing it. Attach/detach/repos "
            "read only the config (no token, no network); init --from-github "
            "and import still scan GitHub (read-only) but write nothing",
        )
        parser = argparse.ArgumentParser(
            prog="gdkm",
            parents=[common],
            description="Move GitHub deploy keys between repos.",
            epilog="subcommands: status, init, import, repos",
        )
        parser.add_argument("--key", metavar="NICK", help="key nickname in the config")
        parser.add_argument("--repo", metavar="REPO", help="name or owner/name")
        parser.add_argument(
            "--rw", action="store_true", help="read-write (default: read-only)"
        )
        parser.add_argument(
            "--detach", action="store_true", help="remove the key from its repo"
        )
        sub = parser.add_subparsers(dest="command")
        sub.add_parser(
            "status", parents=[common], help="compare the config with GitHub"
        )
        init = sub.add_parser("init", parents=[common], help="write a starter config")
        init.add_argument("--user", help="your GitHub user name")
        init.add_argument(
            "--from-github",
            action="store_true",
            help="fill the config with the deploy keys found on GitHub",
        )
        org = {"action": "append", "metavar": "NAME", "default": []}
        org_help = "scan this user/org (repeatable; default: github_user)"
        init.add_argument("--org", help=org_help, **org)
        imp = sub.add_parser(
            "import", parents=[common], help="merge deploy keys found on GitHub"
        )
        imp.add_argument("--org", help=org_help, **org)
        repos = sub.add_parser("repos", help="manage the list of repos")
        actions = repos.add_subparsers(dest="action", required=True)
        for action, text in (("add", "add repos"), ("remove", "remove repos")):
            act = actions.add_parser(action, parents=[common], help=text)
            act.add_argument("names", nargs="+", metavar="NAME")
        actions.add_parser("list", parents=[common], help="list repos and their keys")
        return parser

    def _validate(self, args: argparse.Namespace) -> None:
        flat = args.key or args.repo or args.rw or args.detach
        if args.command == "status":
            if flat or args.dry_run:
                self.parser.error("status takes no other options")
        elif args.command:
            if flat:
                self.parser.error(f"{args.command} takes no --key/--repo/--rw/--detach")
            if args.command == "init":
                if not args.from_github and not args.user:
                    self.parser.error("init needs --user (or --from-github)")
                if args.org and not args.from_github:
                    self.parser.error("--org needs --from-github")
        elif not args.key:
            self.parser.error("--key is required (or use a subcommand)")
        elif args.detach and (args.repo or args.rw):
            self.parser.error("--detach cannot be combined with --repo/--rw")
        elif not args.detach and not args.repo:
            self.parser.error("--repo is required (or use --detach)")

    def _init(self, args: argparse.Namespace, path: str) -> None:
        if not args.from_github:
            if args.dry_run:
                print(f"would write a starter config to {path}")
                return
            Config.init(path, args.user)
            print(f"wrote {path}")
            return
        if os.path.exists(path):  # fail early, before any GitHub call
            raise ConfigError(f"{path} already exists; refusing to overwrite")
        scanner = GitHubScanner(self.client)
        user = args.user or scanner.login()
        scan = scanner.scan(args.org or [user])
        text = STARTER_CONFIG.format(user=user)
        if args.dry_run:
            config = Config(path, text)
        else:
            Config.init(path, user)
            config = Config(path)
        report = ConfigMerger(config).merge(scan)
        if args.dry_run:
            print(f"dry run: would write {path}")
        else:
            config.save()
            print(f"wrote {path}")
        print("\n".join(report.render()))

    def _import(self, args: argparse.Namespace, path: str) -> None:
        config = Config(path)
        scanner = GitHubScanner(self.client)
        report = ConfigMerger(config).merge(
            scanner.scan(args.org or [config.github_user])
        )
        if args.dry_run:
            print(f"dry run: would update {path}")
        else:
            config.save()
        print("\n".join(report.render()))

    def _repos(self, args: argparse.Namespace, path: str) -> None:
        repo_list = RepoList(Config(path), self.client, dry_run=args.dry_run)
        if args.action == "list":
            repo_list.show()
        elif args.action == "add":
            repo_list.add(args.names)
        else:
            repo_list.remove(args.names)

    def run(self, argv: Optional[list[str]] = None) -> int:
        """Parse argv, dispatch, and return the exit code."""
        args = self.parser.parse_args(argv)
        # argparse.SUPPRESS keeps a sub-parser from resetting a value given
        # before the subcommand, so the attribute may be missing.
        args.dry_run = getattr(args, "dry_run", False)
        path = getattr(args, "config", None) or Config.default_path()
        self._validate(args)
        try:
            if args.command == "init":
                self._init(args, path)
            elif args.command == "import":
                self._import(args, path)
            elif args.command == "repos":
                self._repos(args, path)
            elif args.command == "status":
                return KeyManager(Config(path), self.client).status()
            else:
                manager = KeyManager(Config(path), self.client, args.dry_run)
                if args.detach:
                    manager.detach(args.key)
                else:
                    manager.attach(args.key, args.repo, args.rw)
            return 0
        except DeployKeyManagerError as err:
            print(f"error: {err}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            return 130


def main(argv: Optional[list[str]] = None) -> int:
    """Entry point."""
    return Cli().run(argv)


if __name__ == "__main__":
    sys.exit(main())
