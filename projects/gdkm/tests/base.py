"""Shared test case: temp config, fake GitHub, CLI runner."""

import contextlib
import io
import os
import tempfile
import unittest

from gdkm import Cli, Config, GitHubClient
from tests.fakes import FakeGitHub, FakeTokenProvider, make_key

LAPTOP = make_key(1, "laptop@example")
CI = make_key(2, "ci@example")

CONFIG = f"""\
# my comment
github_user = "fcami"
repos = ["fcami/foo"]  # inline

[keys.laptop]
pubkey = "{LAPTOP}"
repo = ""
mode = "ro"

[keys.ci]
pubkey = "{CI}"
repo = ""
mode = "ro"
"""


class CliTestCase(unittest.TestCase):
    """Base: temp config, fake GitHub, CLI runner."""

    def setUp(self) -> None:
        # Cleanup is registered right below, so no 'with' block is wanted.
        tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(tmp.cleanup)
        self.path = os.path.join(tmp.name, "config.toml")
        self.write(CONFIG)
        self.gh = FakeGitHub("fcami/foo", "some-org/bar", "fcami/baz")
        self.tokens = FakeTokenProvider()

    def write(self, text: str) -> None:
        """Replace the config file."""
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(text)

    def read(self) -> str:
        """Current config text."""
        with open(self.path, encoding="utf-8") as handle:
            return handle.read()

    def run_cli(self, *argv: str) -> tuple[int, str, str]:
        """Run the CLI; return (exit code, stdout, stderr)."""
        client = GitHubClient(self.tokens, self.gh)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = Cli(client).run(["--config", self.path, *argv])
        return code, out.getvalue(), err.getvalue()

    def cfg(self, nick: str):
        """Reload the config entry for nick."""
        entry = Config(self.path).key(nick)
        return str(entry.repo or ""), entry.mode
