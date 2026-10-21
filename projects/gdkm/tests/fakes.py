"""In-memory fake of the GitHub deploy-key API and of `gh auth token`."""

import base64
import json
import re
import struct
import urllib.error
from typing import Optional

from gdkm import HttpRequest, HttpResponse

TOKEN = "ghp_faketoken123"
API = "https://api.github.com"


def make_key(seed: int, comment: str = "") -> str:
    """Build a structurally valid ssh-ed25519 public key line."""
    name = b"ssh-ed25519"
    raw = struct.pack(">I", len(name)) + name + struct.pack(">I", 32)
    raw += bytes([seed]) * 32
    line = "ssh-ed25519 " + base64.b64encode(raw).decode()
    return f"{line} {comment}".strip()


def err_body(message: str, *details: str) -> bytes:
    """JSON error body in GitHub's format."""
    errors = [
        {"resource": "PublicKey", "code": "custom", "message": m} for m in details
    ]
    return json.dumps({"message": message, "errors": errors}).encode()


class FakeTokenProvider:  # pylint: disable=too-few-public-methods
    """Stands in for `gh auth token`; counts invocations."""

    def __init__(self, token: str = TOKEN, error: Optional[Exception] = None) -> None:
        self.token, self.error, self.calls = token, error, 0

    def __call__(self) -> str:
        self.calls += 1
        if self.error:
            raise self.error
        return self.token


class FakeGitHub:  # pylint: disable=too-many-instance-attributes
    """Transport enforcing "one key, one repo on all of GitHub"."""

    def __init__(self, *repos: str) -> None:
        self.repos: dict[str, dict[int, dict]] = {r: {} for r in repos}
        self.next_id = 1
        self.calls: list[tuple[str, str]] = []
        self.posts = 0
        self.fail_posts: set[int] = set()  # make the Nth POST answer 500
        self.forced: dict[str, tuple[int, bytes]] = {}  # "METHOD path" -> response
        self.network_down = False
        self.page_size = 100
        self.login = "fcami"  # the token's owner, answered by GET /user
        self.archived: set[str] = set()
        self.private: set[str] = set()
        self.no_admin: set[str] = set()  # repos whose keys answer 403

    def put(
        self, repo: str, line: str, read_only: bool = True, title: str = "seed"
    ) -> int:
        """Seed a deploy key directly."""
        kid = self.next_id
        self.next_id += 1
        self.repos[repo][kid] = {
            "id": kid,
            "key": " ".join(line.split()[:2]),
            "title": title,
            "read_only": read_only,
        }
        return kid

    def where(self, line: str) -> Optional[tuple[str, dict]]:
        """Return (repo, key dict) holding the key, if any."""
        ident = " ".join(line.split()[:2])
        for repo, keys in self.repos.items():
            for key in keys.values():
                if key["key"] == ident:
                    return repo, key
        return None

    def mutations(self) -> list[tuple[str, str]]:
        """All POST/DELETE calls seen."""
        return [c for c in self.calls if c[0] != "GET"]

    def request(self, req: HttpRequest) -> HttpResponse:
        """Answer one request like api.github.com would."""
        if self.network_down:
            raise urllib.error.URLError("fake network down")
        path = req.url[len(API) :].split("?")[0]
        self.calls.append((req.method, path))
        early = self._early_answer(req, path)
        if early:
            return early
        match = re.fullmatch(r"/repos/([^/]+/[^/]+)/keys(?:/(\d+))?", path)
        repo = match.group(1) if match else ""
        if repo not in self.repos:
            return HttpResponse(404, {}, err_body("Not Found"))
        if repo in self.no_admin:
            return HttpResponse(
                403, {}, err_body("Must have admin rights to Repository.")
            )
        if req.method == "GET":
            return self._list(repo, req.url)
        if req.method == "POST":
            return self._post(repo, req)
        return self._delete(repo, int(match.group(2)))

    def _early_answer(self, req: HttpRequest, path: str) -> Optional[HttpResponse]:
        """Auth check, forced answers and the repo-listing endpoints."""
        if req.headers.get("Authorization") != f"Bearer {TOKEN}":
            return HttpResponse(401, {}, err_body("Bad credentials"))
        forced = self.forced.get(f"{req.method} {path}")
        if forced:
            return HttpResponse(forced[0], {}, forced[1])
        return self._repo_listing(path, req.url)

    def _repo_listing(self, path: str, url: str) -> Optional[HttpResponse]:
        """Answer GET /user, /user/repos and /orgs/NAME/repos."""
        if path == "/user":
            return HttpResponse(200, {}, json.dumps({"login": self.login}).encode())
        org = re.fullmatch(r"/orgs/([^/]+)/repos", path)
        if path != "/user/repos" and not org:
            return None
        owner = org.group(1) if org else self.login
        names = [r for r in self.repos if r.split("/")[0] == owner]
        if org and (not names or owner == self.login):
            return HttpResponse(404, {}, err_body("Not Found"))
        items = [
            {
                "full_name": r,
                "private": r in self.private,
                "archived": r in self.archived,
            }
            for r in names
        ]
        return self._page(items, url, path)

    def _page(self, items: list[dict], url: str, path: str) -> HttpResponse:
        page = int((re.search(r"[?&]page=(\d+)", url) or [0, 1])[1])
        size = self.page_size
        headers = {}
        if page * size < len(items):
            headers["link"] = (
                f'<{API}{path}?per_page={size}&page={page + 1}>; rel="next"'
            )
        chunk = items[(page - 1) * size : page * size]
        return HttpResponse(200, headers, json.dumps(chunk).encode())

    def _list(self, repo: str, url: str) -> HttpResponse:
        return self._page(list(self.repos[repo].values()), url, f"/repos/{repo}/keys")

    def _post(self, repo: str, req: HttpRequest) -> HttpResponse:
        self.posts += 1
        if self.posts in self.fail_posts:
            return HttpResponse(500, {}, err_body("Server Error"))
        body = json.loads(req.body)
        if self.where(body["key"]):
            return HttpResponse(
                422, {}, err_body("Validation Failed", "key is already in use")
            )
        kid = self.put(repo, body["key"], body["read_only"])
        self.repos[repo][kid]["title"] = body["title"]
        return HttpResponse(201, {}, json.dumps(self.repos[repo][kid]).encode())

    def _delete(self, repo: str, kid: int) -> HttpResponse:
        if self.repos[repo].pop(kid, None) is None:
            return HttpResponse(404, {}, err_body("Not Found"))
        return HttpResponse(204, {}, b"")
