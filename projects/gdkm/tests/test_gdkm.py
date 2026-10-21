"""Tests for gdkm against a fake GitHub; no network, no real gh."""

import contextlib
import io
import os
import stat
import subprocess
import unittest
from unittest import mock

from gdkm import (
    Config,
    DeployKeyManagerError,
    GitHubAuthError,
    GhTokenProvider,
    GitHubClient,
    InvalidInputError,
    PublicKey,
    Repo,
)
from tests.base import CI, CONFIG, LAPTOP, CliTestCase
from tests.fakes import FakeTokenProvider, make_key


class UnitTests(unittest.TestCase):
    """Value objects and Config."""

    def test_public_key(self) -> None:
        """Comment is ignored when comparing; junk is rejected."""
        self.assertTrue(
            PublicKey.parse(make_key(1, "a")).same_key(PublicKey.parse(make_key(1)))
        )
        self.assertFalse(PublicKey.parse(make_key(1)).same_key(PublicKey.parse(CI)))
        for bad in (
            "",
            "ssh-ed25519",
            "ssh-foo AAAA",
            "ssh-ed25519 !!!",
            "ssh-rsa " + CI[12:],
        ):
            with self.assertRaises(InvalidInputError, msg=bad):
                PublicKey.parse(bad)

    def test_repo(self) -> None:
        """Short names get the default owner; malformed ones fail."""
        self.assertEqual(str(Repo.parse("foo", "fcami")), "fcami/foo")
        self.assertEqual(str(Repo.parse("org/foo", "fcami")), "org/foo")
        for bad in ("a/b/c", "/foo", "foo/", "a b/c", "../x", "o/.."):
            with self.assertRaises(InvalidInputError, msg=bad):
                Repo.parse(bad, "fcami")
        with self.assertRaises(InvalidInputError):
            Repo.parse("foo", "")


class ConfigTests(CliTestCase):
    """Config loading, saving and error messages."""

    def test_unknown_key_lists_known(self) -> None:
        """US-10: unknown nickname."""
        code, _, err = self.run_cli("--key", "nope", "--repo", "foo")
        self.assertEqual(code, 1)
        self.assertIn("laptop, ci", err)

    def test_bad_configs(self) -> None:
        """US-10: missing file, bad TOML, no pubkey, bad pubkey, bad mode."""
        os.unlink(self.path)
        self.assertIn("not found", self.run_cli("status")[2])
        for text, expect in (
            ("this is = = bad", "not valid TOML"),
            ('[keys.a]\nrepo = ""\n', "no pubkey"),
            ('[keys.a]\npubkey = "hello world"\n', "unsupported"),
            (f'[keys.a]\npubkey = "{LAPTOP}"\nmode = "x"\n', "mode"),
        ):
            self.write(text)
            code, _, err = self.run_cli("status")
            self.assertEqual(code, 1)
            self.assertIn(expect, err)

    def test_save_keeps_comments_and_mode(self) -> None:
        """US-9: comments, order and permissions survive a save."""
        os.chmod(self.path, 0o600)
        self.assertEqual(self.run_cli("--key", "laptop", "--repo", "baz")[0], 0)
        text = self.read()
        self.assertIn("# my comment", text)
        self.assertIn("# inline", text)
        self.assertLess(text.index("laptop"), text.index("keys.ci"))
        self.assertEqual(stat.S_IMODE(os.stat(self.path).st_mode), 0o600)
        self.assertEqual(
            [f for f in os.listdir(os.path.dirname(self.path)) if f != "config.toml"],
            [],
        )

    def test_init(self) -> None:
        """US-14: init writes a loadable config and never overwrites."""
        os.unlink(self.path)
        self.assertEqual(self.run_cli("init", "--user", "fcami")[0], 0)
        self.assertEqual(Config(self.path).github_user, "fcami")
        before = self.read()
        code, _, err = self.run_cli("init", "--user", "other")
        self.assertEqual(code, 1)
        self.assertIn("refusing to overwrite", err)
        self.assertEqual(self.read(), before)
        self.assertEqual(self.tokens.calls, 0)

    def test_usage_errors(self) -> None:
        """Bad option combinations exit 2."""
        for argv in (
            ["--repo", "foo"],
            ["--key", "laptop"],
            ["--key", "laptop", "--detach", "--rw"],
            ["status", "--key", "laptop"],
        ):
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    self.run_cli(*argv)
            self.assertEqual(ctx.exception.code, 2, argv)


class AttachTests(CliTestCase):
    """US-1 .. US-8."""

    def test_attach_ro(self) -> None:
        """US-1, US-5, US-6."""
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "foo")
        self.assertEqual((code, out), (0, "laptop: (none) -> fcami/foo [ro]\n"))
        where = self.gh.where(LAPTOP)
        self.assertEqual(where[0], "fcami/foo")
        self.assertTrue(where[1]["read_only"])
        self.assertEqual(where[1]["title"], "laptop")
        self.assertEqual(self.cfg("laptop"), ("fcami/foo", "ro"))
        self.assertEqual(Config(self.path).repos, [Repo("fcami", "foo")])

    def test_attach_rw_new_repo_appended(self) -> None:
        """US-2, US-6: --rw, new repo appended once, order kept."""
        self.run_cli("--key", "laptop", "--repo", "some-org/bar", "--rw")
        self.assertFalse(self.gh.where(LAPTOP)[1]["read_only"])
        self.assertEqual(self.cfg("laptop"), ("some-org/bar", "rw"))
        self.run_cli("--key", "ci", "--repo", "some-org/bar")
        self.assertEqual(
            [str(r) for r in Config(self.path).repos], ["fcami/foo", "some-org/bar"]
        )

    def test_move(self) -> None:
        """US-3: removed from old repo before add; output shows both ends."""
        self.run_cli("--key", "laptop", "--repo", "foo")
        self.gh.calls.clear()
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "some-org/bar", "--rw")
        self.assertEqual(code, 0)
        self.assertEqual(out, "laptop: fcami/foo [ro] -> some-org/bar [rw]\n")
        self.assertEqual([c[0] for c in self.gh.mutations()], ["DELETE", "POST"])
        self.assertEqual(self.gh.where(LAPTOP)[0], "some-org/bar")
        self.assertEqual(self.cfg("laptop"), ("some-org/bar", "rw"))

    def test_mode_change_and_noop(self) -> None:
        """US-4: same repo other mode = delete + add; same mode = no-op."""
        self.run_cli("--key", "laptop", "--repo", "foo")
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "foo", "--rw")
        self.assertEqual(out, "laptop: fcami/foo [ro] -> fcami/foo [rw]\n")
        self.assertFalse(self.gh.where(LAPTOP)[1]["read_only"])
        self.gh.calls.clear()
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "foo", "--rw")
        self.assertEqual(code, 0)
        self.assertIn("already attached", out)
        self.assertEqual(self.gh.mutations(), [])

    def test_rollback_restores_previous(self) -> None:
        """US-7: failed add (no such repo) puts the key back; config untouched."""
        self.run_cli("--key", "laptop", "--repo", "foo", "--rw")
        before = self.read()
        code, _, err = self.run_cli("--key", "laptop", "--repo", "nonexistent")
        self.assertEqual(code, 1)
        self.assertIn("rolled back to fcami/foo [rw]", err)
        where = self.gh.where(LAPTOP)
        self.assertEqual((where[0], where[1]["read_only"]), ("fcami/foo", False))
        self.assertEqual(self.read(), before)

    def test_rollback_failure(self) -> None:
        """US-7: rollback fails too -> says attached nowhere."""
        self.run_cli("--key", "laptop", "--repo", "foo")
        before = self.read()
        self.gh.fail_posts = {2, 3}
        code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 1)
        self.assertIn("attached NOWHERE", err)
        self.assertIsNone(self.gh.where(LAPTOP))
        self.assertEqual(self.read(), before)

    def test_failure_without_previous(self) -> None:
        """A failed first attach changes nothing."""
        before = self.read()
        code, _, err = self.run_cli("--key", "laptop", "--repo", "nonexistent")
        self.assertEqual(code, 1)
        self.assertIn("nothing to roll back", err)
        self.assertEqual(self.read(), before)

    def test_drift_missing_from_recorded_repo(self) -> None:
        """US-8: key gone from the recorded repo -> warn, no delete, go on."""
        self.write(CONFIG.replace('repo = ""', 'repo = "fcami/foo"', 1))
        code, out, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 0)
        self.assertIn("not found on fcami/foo", err)
        self.assertEqual([c[0] for c in self.gh.mutations()], ["POST"])
        self.assertEqual(out, "laptop: (none) -> fcami/baz [ro]\n")

    def test_drift_found_on_other_managed_repo(self) -> None:
        """US-8: 422 -> search managed repos, remove there, retry."""
        self.write(CONFIG.replace('["fcami/foo"]', '["fcami/foo", "some-org/bar"]'))
        self.gh.put("some-org/bar", LAPTOP)
        code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 0)
        self.assertIn("actually on some-org/bar", err)
        self.assertEqual(self.gh.where(LAPTOP)[0], "fcami/baz")
        self.assertEqual(self.cfg("laptop"), ("fcami/baz", "ro"))

    def test_drift_unmanaged_repo(self) -> None:
        """US-8: key in use on an unmanaged repo -> error, config unchanged."""
        self.gh.put("some-org/bar", LAPTOP)
        before = self.read()
        code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 1)
        self.assertIn("not managed", err)
        self.assertEqual(self.gh.where(LAPTOP)[0], "some-org/bar")
        self.assertEqual(self.read(), before)

    def test_drift_already_on_unmanaged_target(self) -> None:
        """US-8: key already on the target, which is not in repos yet."""
        self.gh.put("fcami/baz", LAPTOP)
        code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 0)
        self.assertIn("actually on fcami/baz", err)
        self.assertEqual(self.gh.where(LAPTOP)[0], "fcami/baz")
        self.assertEqual(self.cfg("laptop"), ("fcami/baz", "ro"))

    def test_config_resynced_when_github_already_right(self) -> None:
        """Key is on the target but the config said otherwise: fix the config."""
        self.gh.put("fcami/foo", LAPTOP)
        self.write(CONFIG.replace('repo = ""', 'repo = "fcami/foo"', 1))
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "foo", "--rw")
        self.assertEqual(code, 0)
        self.assertIn("fcami/foo [ro] -> fcami/foo [rw]", out)

    def test_bad_repo_name(self) -> None:
        """Malformed names are rejected before any call."""
        code, _, err = self.run_cli("--key", "laptop", "--repo", "a/b/c")
        self.assertEqual(code, 1)
        self.assertIn("malformed", err)
        self.assertEqual(self.gh.calls, [])


class OtherCommandTests(CliTestCase):
    """Detach, status, dry-run."""

    def test_detach(self) -> None:
        """US-12."""
        self.run_cli("--key", "laptop", "--repo", "foo")
        code, out, _ = self.run_cli("--key", "laptop", "--detach")
        self.assertEqual((code, out), (0, "laptop: fcami/foo [ro] -> (none)\n"))
        self.assertIsNone(self.gh.where(LAPTOP))
        self.assertEqual(self.cfg("laptop")[0], "")
        code, out, _ = self.run_cli("--key", "laptop", "--detach")
        self.assertEqual((code, out), (0, "laptop: not attached\n"))

    def test_status(self) -> None:
        """US-11: ok / missing / mode differs / unattached."""
        self.run_cli("--key", "laptop", "--repo", "foo")
        self.write(self.read().replace('repo = ""', 'repo = "some-org/bar"'))
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 0)
        self.assertRegex(out, r"laptop\s+fcami/foo\s+ro\s+ok")
        self.assertRegex(out, r"ci\s+some-org/bar\s+ro\s+missing")
        self.gh.put("some-org/bar", CI, read_only=False)
        self.assertRegex(
            self.run_cli("status")[1], r"ci\s+some-org/bar\s+ro\s+mode differs"
        )
        self.run_cli("--key", "ci", "--detach")
        self.assertRegex(self.run_cli("status")[1], r"ci\s+-\s+ro\s+unattached")

    def test_status_error_exit_code(self) -> None:
        """Status exits 1 if a repo cannot be listed."""
        self.write(self.read().replace('repo = ""', 'repo = "gone/repo"', 1))
        code, out, _ = self.run_cli("status")
        self.assertEqual(code, 1)
        self.assertIn("error:", out)

    def test_dry_run(self) -> None:
        """US-13: prints the plan, touches nothing, needs no token."""
        before = self.read()
        code, out, _ = self.run_cli("--key", "laptop", "--repo", "foo", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would run: POST /repos/fcami/foo/keys", out)
        self.assertIn("read_only=true", out)
        self.assertEqual(self.read(), before)
        self.assertEqual(self.gh.calls, [])
        self.assertEqual(self.tokens.calls, 0)
        self.run_cli("--key", "laptop", "--repo", "foo")
        out = self.run_cli("--key", "laptop", "--detach", "--dry-run")[1]
        self.assertIn("DELETE /repos/fcami/foo/keys", out)
        self.assertEqual(self.cfg("laptop")[0], "fcami/foo")


class ClientTests(CliTestCase):
    """Token handling, HTTP details and error mapping."""

    def test_token_fetched_once_and_lazily(self) -> None:
        """Token requested once per run, only on first real call."""
        self.assertEqual(self.tokens.calls, 0)
        self.run_cli("--key", "laptop", "--repo", "foo", "--rw")
        self.assertEqual(self.tokens.calls, 1)

    def test_token_not_leaked(self) -> None:
        """repr() and error output never contain the token."""
        client = GitHubClient(self.tokens, self.gh)
        client.list_keys(Repo("fcami", "foo"))
        self.assertNotIn("ghp_", repr(client))
        self.gh.forced["GET /repos/fcami/foo/keys"] = (500, b"oops")
        _, out, err = self.run_cli("status")
        self.assertNotIn("ghp_", out + err)

    def test_no_token(self) -> None:
        """gh missing / logged out: clear message."""
        self.tokens = FakeTokenProvider(
            error=GitHubAuthError("no GitHub token from gh; run `gh auth login`")
        )
        code, _, err = self.run_cli("--key", "laptop", "--repo", "foo")
        self.assertEqual(code, 1)
        self.assertIn("gh auth login", err)

    def test_http_errors(self) -> None:
        """401, 403, 404, 500 and network failures map to clear messages."""
        path = "GET /repos/fcami/foo/keys"
        cases = (
            (
                401,
                b'{"message":"Bad credentials"}',
                "gh auth refresh -h github.com -s repo",
            ),
            (403, b'{"message":"Resource not accessible"}', "Administration"),
            (404, b'{"message":"Not Found"}', "no admin rights"),
            (500, b"<html>", "HTTP 500"),
        )
        for status, body, expect in cases:
            self.gh.forced[path] = (status, body)
            self.write(CONFIG.replace('repo = ""', 'repo = "fcami/foo"', 1))
            code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
            self.assertEqual(code, 1, status)
            self.assertIn(expect, err)
        self.gh.forced.clear()
        self.gh.network_down = True
        code, _, err = self.run_cli("--key", "laptop", "--repo", "baz")
        self.assertEqual(code, 1)
        self.assertIn("network error", err)

    def test_wrong_token_rejected_by_fake(self) -> None:
        """Sanity: the fake really checks the Bearer header."""
        self.tokens = FakeTokenProvider(token="other")
        code, _, err = self.run_cli("--key", "laptop", "--repo", "foo")
        self.assertEqual(code, 1)
        self.assertIn("token rejected", err)

    def test_pagination(self) -> None:
        """Every page is followed via the Link header."""
        self.gh.page_size = 2
        for seed in range(10, 17):
            self.gh.put("fcami/foo", make_key(seed))
        keys = GitHubClient(self.tokens, self.gh).list_keys(Repo("fcami", "foo"))
        self.assertEqual(len(keys), 7)
        self.assertEqual(sum(1 for c in self.gh.calls if c[0] == "GET"), 4)
        self.gh.put("fcami/foo", LAPTOP)
        self.assertIsNotNone(
            GitHubClient(self.tokens, self.gh).find_key(
                Repo("fcami", "foo"), PublicKey.parse(LAPTOP)
            )
        )

    def test_api_errors_are_deploy_key_errors(self) -> None:
        """All client failures share the base class."""
        client = GitHubClient(self.tokens, self.gh)
        with self.assertRaises(DeployKeyManagerError):
            client.list_keys(Repo("no", "such"))

    def test_gh_token_provider(self) -> None:
        """`gh auth token` is mocked; missing gh and failures give clear errors."""
        run = "gdkm.subprocess.run"
        which = "gdkm.shutil.which"
        done = subprocess.CompletedProcess
        with mock.patch(which, return_value=None):
            with self.assertRaisesRegex(GitHubAuthError, "not installed"):
                GhTokenProvider()()
        with mock.patch(which, return_value="/x/gh"):
            with mock.patch(run, return_value=done([], 0, "tok\n", "")) as proc:
                self.assertEqual(GhTokenProvider()(), "tok")
                self.assertEqual(proc.call_args[0][0], ["gh", "auth", "token"])
            with mock.patch(run, return_value=done([], 1, "", "not logged in")):
                with self.assertRaisesRegex(GitHubAuthError, "gh auth login"):
                    GhTokenProvider()()
            with mock.patch(run, return_value=done([], 0, "", "")):
                with self.assertRaisesRegex(GitHubAuthError, "gh auth login"):
                    GhTokenProvider()()


if __name__ == "__main__":
    unittest.main()
