"""Tests for US-15..US-17: GitHub scan, init --from-github, import, repos."""

import contextlib
import io
import os

from gdkm import ConfigMerger, Config, Repo
from tests.base import CONFIG, LAPTOP, CliTestCase
from tests.fakes import make_key

K1, K2, K3, K4, K5, K6, K7 = (make_key(n, f"c{n}@host") for n in range(11, 18))


def flatten(text: str) -> list[str]:
    """Collapse runs of spaces so tables can be compared line by line."""
    return [" ".join(line.split()) for line in text.splitlines()]


class ScanTestCase(CliTestCase):
    """A GitHub with private, archived, empty and non-admin repos."""

    def setUp(self) -> None:
        super().setUp()
        for name in ("fcami/old", "fcami/priv", "fcami/empty", "some-org/secret"):
            self.gh.repos[name] = {}
        self.gh.archived.add("fcami/old")
        self.gh.private.add("fcami/priv")
        self.gh.no_admin.add("some-org/secret")
        self.gh.put("fcami/foo", K1, title="Deploy")
        self.gh.put("fcami/priv", K2, read_only=False, title="deploy")
        self.gh.put("fcami/old", K3, title="Old Key@CI")
        self.gh.put("some-org/bar", K4, title="")
        self.gh.put("some-org/secret", K5, title="hidden")

    def new_config(self) -> None:
        """Remove the config so that init can create it."""
        os.unlink(self.path)

    def keys(self) -> dict:
        """Config keys as {nick: (repo, mode)}."""
        return {
            n: (str(e.repo or ""), e.mode) for n, e in Config(self.path).keys.items()
        }


class InitFromGitHubTests(ScanTestCase):
    """US-15."""

    def test_init_from_github(self) -> None:
        """User from /user, own repos incl. private; summary; archived comment."""
        self.new_config()
        code, out, _ = self.run_cli("init", "--from-github")
        self.assertEqual(code, 0)
        cfg = Config(self.path)
        self.assertEqual(cfg.github_user, "fcami")
        self.assertEqual(
            self.keys(),
            {
                "deploy": ("fcami/foo", "ro"),
                "deploy-priv": ("fcami/priv", "rw"),
                "old-key-ci": ("fcami/old", "ro"),
            },
        )
        # only repos holding a key, in scan order; no repo without keys
        self.assertEqual(
            [str(r) for r in cfg.repos], ["fcami/foo", "fcami/old", "fcami/priv"]
        )
        # pubkey is "type blob": GitHub returns no comment
        self.assertEqual(cfg.keys["deploy"].pubkey.line, " ".join(K1.split()[:2]))
        self.assertIn("deploy-priv fcami/priv rw added", flatten(out))
        self.assertIn("scanned 5 repos, skipped 0 (no admin access)", out)
        self.assertIn("warning: fcami/old is archived", out)
        self.assertRegex(self.read(), r'repo = "fcami/old"\s+# archived')
        self.assertIn(("GET", "/user/repos"), self.gh.calls)
        self.assertEqual(self.gh.mutations(), [])

    def test_user_option_and_org(self) -> None:
        """--user sets github_user; an org is listed via /orgs/NAME/repos."""
        self.new_config()
        code, out, _ = self.run_cli(
            "init", "--from-github", "--user", "me", "--org", "some-org"
        )
        self.assertEqual(code, 0)
        self.assertEqual(Config(self.path).github_user, "me")
        self.assertEqual(self.keys(), {"key": ("some-org/bar", "ro")})
        self.assertIn("scanned 1 repos, skipped 1", out)
        self.assertIn(("GET", "/orgs/some-org/repos"), self.gh.calls)
        self.assertNotIn(("GET", "/user/repos"), self.gh.calls)

    def test_org_equals_form_and_repeat(self) -> None:
        """--org=NAME works, and --org can be repeated."""
        self.new_config()
        code, _, _ = self.run_cli(
            "init", "--from-github", "--org=some-org", "--org", "fcami"
        )
        self.assertEqual(code, 0)
        self.assertEqual(len(self.keys()), 4)
        self.assertEqual(Config(self.path).github_user, "fcami")

    def test_unknown_org(self) -> None:
        """An unknown org is an error and nothing is written."""
        self.new_config()
        code, _, err = self.run_cli("init", "--from-github", "--org", "nosuch")
        self.assertEqual(code, 1)
        self.assertIn("unknown organization", err)
        self.assertFalse(os.path.exists(self.path))

    def test_refuses_to_overwrite(self) -> None:
        """Existing config: refuse before talking to GitHub."""
        before = self.read()
        code, _, err = self.run_cli("init", "--from-github")
        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)
        self.assertEqual(self.read(), before)
        self.assertEqual(self.gh.calls, [])

    def test_dry_run_writes_nothing(self) -> None:
        """--dry-run scans (read-only) and prints, but creates no file."""
        self.new_config()
        code, out, _ = self.run_cli("init", "--from-github", "--dry-run")
        self.assertEqual(code, 0)
        self.assertFalse(os.path.exists(self.path))
        self.assertIn("dry run", out)
        self.assertIn("deploy-priv", out)
        self.assertEqual(self.gh.mutations(), [])

    def test_skipped_repos_and_hard_errors(self) -> None:
        """403/404 on a repo's keys are skipped and counted; others abort."""
        self.new_config()
        self.gh.forced["GET /repos/fcami/baz/keys"] = (404, b'{"message":"Not Found"}')
        self.gh.no_admin.add("fcami/empty")
        code, out, _ = self.run_cli("init", "--from-github")
        self.assertEqual(code, 0)
        self.assertIn("scanned 3 repos, skipped 2", out)
        os.unlink(self.path)
        self.gh.forced["GET /repos/fcami/baz/keys"] = (500, b"boom")
        code, _, err = self.run_cli("init", "--from-github")
        self.assertEqual(code, 1)
        self.assertIn("HTTP 500", err)
        self.assertFalse(os.path.exists(self.path))

    def test_pagination(self) -> None:
        """Repo listings are paginated too."""
        self.new_config()
        self.gh.page_size = 1
        code, out, _ = self.run_cli("init", "--from-github")
        self.assertEqual(code, 0)
        self.assertIn("scanned 5 repos", out)
        self.assertEqual(len(self.keys()), 3)

    def test_nickname_rules(self) -> None:
        """Slug, empty title, repo-name suffix, then a number."""
        merger = ConfigMerger(Config(self.path))
        repo = Repo.parse("fcami/foo")
        self.assertEqual(merger.nickname("My Laptop@Home", repo), "my-laptop-home")
        self.assertEqual(merger.nickname("", repo), "key")
        self.assertEqual(merger.nickname("laptop", repo), "laptop-foo")
        merger.config.keys["laptop-foo"] = merger.config.keys["laptop"]
        self.assertEqual(merger.nickname("laptop", repo), "laptop-foo-2")


class ImportTests(ScanTestCase):
    """US-16."""

    def setUp(self) -> None:
        super().setUp()
        self.gh.put("fcami/baz", LAPTOP, title="whatever")
        self.gh.put("fcami/foo", K6, title="laptop")
        self.gh.put("fcami/foo", K7, title="Laptop")
        self.write(
            CONFIG.replace(
                'repo = ""\nmode = "ro"\n\n[keys.ci]',
                'repo = "fcami/foo"\nmode = "rw"\n\n[keys.ci]',
                1,
            )
        )

    def test_import_merges(self) -> None:
        """fixed / added without nickname clash / not found in scan."""
        code, out, _ = self.run_cli("import")
        self.assertEqual(code, 0)
        flat = flatten(out)
        self.assertIn("laptop fcami/baz ro fixed", flat)
        self.assertIn("ci - ro not found in scan", flat)
        self.assertIn("deploy fcami/foo ro added", flat)
        self.assertIn("laptop-foo fcami/foo ro added", flat)
        self.assertIn("laptop-foo-2 fcami/foo ro added", flat)
        keys = self.keys()
        self.assertEqual(keys["laptop"], ("fcami/baz", "ro"))
        self.assertEqual(keys["ci"], ("", "ro"))
        cfg = Config(self.path)
        # existing key keeps its pubkey line (with comment)
        self.assertEqual(cfg.keys["laptop"].pubkey.line, LAPTOP)
        repos = [str(r) for r in cfg.repos]
        self.assertEqual(repos[0], "fcami/foo")
        self.assertEqual(len(repos), len(set(repos)))
        self.assertIn("fcami/baz", repos)
        self.assertIn("# my comment", self.read())

    def test_import_is_idempotent(self) -> None:
        """A second import changes nothing and reports unchanged."""
        self.run_cli("import")
        after_first = self.read()
        code, out, _ = self.run_cli("import")
        self.assertEqual(code, 0)
        self.assertNotIn("added", out)
        self.assertNotIn("fixed", out)
        self.assertIn("unchanged", out)
        self.assertEqual(self.read(), after_first)

    def test_dry_run(self) -> None:
        """Nothing is written."""
        before = self.read()
        code, out, _ = self.run_cli("import", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertIn("fixed", out)
        self.assertEqual(self.read(), before)
        before_os = os.listdir(os.path.dirname(self.path))
        self.assertEqual(before_os, ["config.toml"])

    def test_org_scan(self) -> None:
        """import --org scans only that org; other keys are 'not found'."""
        code, out, _ = self.run_cli("import", "--org=some-org")
        self.assertEqual(code, 0)
        self.assertIn("key some-org/bar ro added", flatten(out))
        self.assertIn("laptop fcami/foo rw not found in scan", flatten(out))
        self.assertEqual(self.keys()["key"], ("some-org/bar", "ro"))
        self.assertNotIn("deploy", self.keys())
        self.assertEqual(self.keys()["laptop"], ("fcami/foo", "rw"))

    def test_archived_comment_follows_the_key(self) -> None:
        """The archived comment is added by import and dropped on a move."""
        self.run_cli("import")
        self.assertRegex(self.read(), r'repo = "fcami/old"\s+# archived')
        code, _, _ = self.run_cli("--key", "old-key-ci", "--repo", "foo")
        self.assertEqual(code, 0)
        self.assertNotIn("archived", self.read())

    def test_missing_config(self) -> None:
        """import needs an existing config."""
        os.unlink(self.path)
        code, _, err = self.run_cli("import")
        self.assertEqual(code, 1)
        self.assertIn("not found", err)


class ReposTests(ScanTestCase):
    """US-17."""

    def setUp(self) -> None:
        super().setUp()
        self.write(
            CONFIG.replace('["fcami/foo"]', '["fcami/foo", "some-org/bar"]').replace(
                'repo = ""', 'repo = "fcami/foo"', 1
            )
        )

    def repos(self) -> list:
        """Current repos list."""
        return [str(r) for r in Config(self.path).repos]

    def test_add(self) -> None:
        """Short and full names; duplicates ignored; one save."""
        code, out, _ = self.run_cli("repos", "add", "baz", "other/x", "foo", "baz")
        self.assertEqual(code, 1)  # other/x does not exist
        self.assertEqual(self.repos(), ["fcami/foo", "some-org/bar"])
        self.gh.repos["other/x"] = {}
        code, out, _ = self.run_cli("repos", "add", "baz", "other/x", "foo", "baz")
        self.assertEqual(code, 0)
        self.assertIn("fcami/foo: already managed", out)
        self.assertEqual(
            self.repos(), ["fcami/foo", "some-org/bar", "fcami/baz", "other/x"]
        )
        self.assertIn("# my comment", self.read())

    def test_add_rejects_missing_and_non_admin(self) -> None:
        """Nothing is added if any repo is missing or not administered."""
        for bad in ("nonexistent", "some-org/secret"):
            before = self.read()
            code, _, err = self.run_cli("repos", "add", "baz", bad)
            self.assertEqual(code, 1, bad)
            self.assertIn("cannot add", err)
            self.assertEqual(self.read(), before)

    def test_add_dry_run(self) -> None:
        """--dry-run works before or after the subcommand; no token, no calls."""
        before = self.read()
        for argv in (
            ["repos", "add", "baz", "--dry-run"],
            ["--dry-run", "repos", "add", "baz"],
        ):
            code, out, _ = self.run_cli(*argv)
            self.assertEqual(code, 0)
            self.assertIn("would add fcami/baz", out)
        self.assertEqual(self.read(), before)
        self.assertEqual(self.gh.calls, [])
        self.assertEqual(self.tokens.calls, 0)

    def test_remove_refused_while_key_recorded(self) -> None:
        """The error names the key; the config is untouched."""
        before = self.read()
        code, _, err = self.run_cli("repos", "remove", "some-org/bar", "foo")
        self.assertEqual(code, 1)
        self.assertIn("'laptop'", err)
        self.assertIn("fcami/foo", err)
        self.assertEqual(self.read(), before)

    def test_remove(self) -> None:
        """Unreferenced repos are removed; unknown ones are mentioned."""
        code, out, _ = self.run_cli("repos", "remove", "some-org/bar", "nothere")
        self.assertEqual(code, 0)
        self.assertIn("fcami/nothere: not in repos", out)
        self.assertEqual(self.repos(), ["fcami/foo"])
        self.assertEqual(self.gh.calls, [])

    def test_remove_dry_run(self) -> None:
        """Nothing changes."""
        before = self.read()
        code, out, _ = self.run_cli("repos", "remove", "some-org/bar", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would remove some-org/bar", out)
        self.assertEqual(self.read(), before)

    def test_list(self) -> None:
        """Each repo with the nicknames recorded on it."""
        code, out, _ = self.run_cli("repos", "list")
        self.assertEqual(code, 0)
        self.assertEqual(
            [" ".join(line.split()) for line in out.splitlines()],
            ["fcami/foo laptop", "some-org/bar -"],
        )


class UsageTests(CliTestCase):
    """Argument validation for the new commands."""

    def test_usage_errors(self) -> None:
        """Exit status 2."""
        for argv in (
            ["init"],
            ["init", "--org", "x", "--user", "u"],
            ["repos"],
            ["repos", "add"],
            ["import", "--key", "laptop"],
            ["status", "--dry-run"],
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    self.run_cli(*argv)
            self.assertEqual(ctx.exception.code, 2, argv)

    def test_plain_init_dry_run(self) -> None:
        """init --user --dry-run writes nothing."""
        os.unlink(self.path)
        code, out, _ = self.run_cli("init", "--user", "u", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would write", out)
        self.assertFalse(os.path.exists(self.path))
