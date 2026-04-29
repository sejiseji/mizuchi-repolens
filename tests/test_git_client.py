from __future__ import annotations

import subprocess
import unittest

from mizuchi.git import GitClient, GitClientError, GitTimeoutError, validate_commit_hash, validate_relative_path


def test_git_client_allows_only_read_only_verbs() -> None:
    client = GitClient("/repo", runner=_runner(stdout="ok"))

    assert client.log(["--oneline"]) == "ok"

    with unittest.TestCase().assertRaises(GitClientError):
        client.run("checkout", ["main"])


def test_git_client_uses_argument_array_and_timeout() -> None:
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, "ok", "")

    client = GitClient("/repo", timeout_seconds=1.25, runner=runner)
    client.show(["abc1234"])

    command, kwargs = calls[0]
    assert command == ["git", "-C", "/repo", "show", "abc1234"]
    assert kwargs["timeout"] == 1.25
    assert "shell" not in kwargs


def test_git_client_converts_subprocess_timeout() -> None:
    def runner(command, **kwargs):
        raise subprocess.TimeoutExpired(command, timeout=kwargs["timeout"])

    with unittest.TestCase().assertRaises(GitTimeoutError):
        GitClient("/repo", runner=runner).diff(["abc1234^!"])


def test_commit_hash_validation() -> None:
    assert validate_commit_hash("ABC1234") == "abc1234"

    for value in ("main", "HEAD", "abc123", "g" * 40, "abc1234 --help"):
        with unittest.TestCase().assertRaises(GitClientError):
            validate_commit_hash(value)


def test_relative_path_validation_rejects_escape_and_options() -> None:
    assert validate_relative_path("src/app.py") == "src/app.py"

    for value in ("../secret", "/tmp/file", "--output=/tmp/x", "src/.git/config", ""):
        with unittest.TestCase().assertRaises(GitClientError):
            validate_relative_path(value)


def test_diff_result_truncates_by_bytes() -> None:
    client = GitClient("/repo", runner=_runner(stdout="abcdef"))
    result = client.diff_result("abc1234", path="src/app.py", max_bytes=3)

    assert result.diff_text == "abc"
    assert result.truncated is True
    assert result.path == "src/app.py"


def _runner(stdout: str):
    def run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, stdout, "")

    return run
