"""Subprocess boundary for read-only Git commands."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from mizuchi.contracts.models import DiffResult


DEFAULT_GIT_TIMEOUT_SECONDS = 5.0
DEFAULT_DIFF_MAX_BYTES = 200_000
ALLOWED_GIT_VERBS = frozenset({"log", "show", "diff"})
COMMIT_HASH_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
Runner = Callable[..., subprocess.CompletedProcess[str]]


class GitClientError(ValueError):
    """Raised when a git request is unsafe or malformed."""


class GitCommandError(RuntimeError):
    """Raised when an allowed git command fails."""


class GitTimeoutError(TimeoutError):
    """Raised when git exceeds the configured timeout."""


def is_valid_commit_hash(value: str) -> bool:
    """Return whether *value* looks like a short or full Git object hash."""

    return bool(COMMIT_HASH_RE.fullmatch(value))


def validate_commit_hash(value: str) -> str:
    """Validate and normalize a commit hash string."""

    if not is_valid_commit_hash(value):
        raise GitClientError(f"Invalid commit hash: {value!r}")
    return value.lower()


def validate_relative_path(path: str | None) -> str | None:
    """Validate a project-relative path used as a Git pathspec."""

    if path is None:
        return None
    if not path or path.startswith("-"):
        raise GitClientError("Git path must be non-empty and may not start with '-'.")
    posix_path = path.replace("\\", "/")
    parsed = PurePosixPath(posix_path)
    if parsed.is_absolute() or ".." in parsed.parts or ".git" in parsed.parts:
        raise GitClientError(f"Unsafe git path: {path!r}")
    return posix_path


@dataclass(frozen=True)
class GitClient:
    """Small read-only Git client with an explicit command allowlist."""

    repo_path: str
    timeout_seconds: float = DEFAULT_GIT_TIMEOUT_SECONDS
    runner: Runner = subprocess.run

    def run(self, verb: str, args: Sequence[str] = ()) -> str:
        """Run one allowed Git command and return stdout."""

        if verb not in ALLOWED_GIT_VERBS:
            raise GitClientError(f"Forbidden git command: {verb!r}")

        command = ["git", "-C", self.repo_path, verb, *list(args)]
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise GitTimeoutError(f"git {verb} timed out after {self.timeout_seconds}s") from exc

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            raise GitCommandError(stderr or f"git {verb} failed with exit code {completed.returncode}")
        return completed.stdout

    def log(self, args: Sequence[str] = ()) -> str:
        return self.run("log", args)

    def show(self, args: Sequence[str] = ()) -> str:
        return self.run("show", args)

    def diff(self, args: Sequence[str] = ()) -> str:
        return self.run("diff", args)

    def diff_result(
        self,
        commit_hash: str,
        path: str | None = None,
        max_bytes: int = DEFAULT_DIFF_MAX_BYTES,
    ) -> DiffResult:
        """Return a safely truncated diff for a commit or a path in that commit."""

        safe_hash = validate_commit_hash(commit_hash)
        safe_path = validate_relative_path(path)
        if max_bytes < 1:
            raise GitClientError("max_bytes must be positive.")

        args = [f"{safe_hash}^!", "--"]
        if safe_path is not None:
            args.append(safe_path)

        diff_text = self.diff(args)
        encoded = diff_text.encode("utf-8")
        truncated = len(encoded) > max_bytes
        if truncated:
            diff_text = encoded[:max_bytes].decode("utf-8", errors="ignore")

        return DiffResult(
            commit_hash=safe_hash,
            path=safe_path,
            diff_text=diff_text,
            truncated=truncated,
            max_bytes=max_bytes,
        )
