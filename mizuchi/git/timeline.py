"""Timeline, commit detail, and diff extraction helpers."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from mizuchi.contracts.models import DiffResult, GitCommitDetail, GitCommitSummary
from mizuchi.git.client import (
    DEFAULT_DIFF_MAX_BYTES,
    GitClient,
    GitClientError,
    validate_commit_hash,
    validate_relative_path,
)


FIELD_SEP = "\x1f"
LOG_FORMAT = f"%H{FIELD_SEP}%h{FIELD_SEP}%cI{FIELD_SEP}%an{FIELD_SEP}%s"
DETAIL_FORMAT = f"%H{FIELD_SEP}%h{FIELD_SEP}%cI{FIELD_SEP}%an{FIELD_SEP}%s{FIELD_SEP}%b"


def get_timeline(
    client: GitClient,
    depth: int = 50,
    selected_file: str | None = None,
) -> tuple[GitCommitSummary, ...]:
    """Extract recent commits with changed-file counts and optional file touch flags."""

    if depth < 1:
        raise GitClientError("depth must be positive.")
    safe_selected_file = validate_relative_path(selected_file)
    args = [f"-n{depth}", "--date=iso-strict", f"--pretty=format:{LOG_FORMAT}", "--numstat"]
    if safe_selected_file is not None:
        args.extend(["--", safe_selected_file])
    raw = client.log(args)
    return parse_timeline(raw, selected_file=safe_selected_file)


def get_commit_detail(client: GitClient, commit_hash: str) -> GitCommitDetail:
    """Extract one commit's metadata, body, and changed files."""

    safe_hash = validate_commit_hash(commit_hash)
    raw = client.show(
        [
            "--date=iso-strict",
            f"--pretty=format:{DETAIL_FORMAT}",
            "--name-only",
            "--no-renames",
            safe_hash,
        ]
    )
    return parse_commit_detail(raw)


def get_commit_diff(
    client: GitClient,
    commit_hash: str,
    path: str | None = None,
    max_bytes: int = DEFAULT_DIFF_MAX_BYTES,
) -> DiffResult:
    """Extract a truncated read-only diff for a commit or path."""

    return client.diff_result(commit_hash=commit_hash, path=path, max_bytes=max_bytes)


def parse_timeline(raw: str, selected_file: str | None = None) -> tuple[GitCommitSummary, ...]:
    commits: list[GitCommitSummary] = []
    current: _CommitAccumulator | None = None

    for line in raw.splitlines():
        if FIELD_SEP in line:
            if current is not None:
                commits.append(current.to_summary(selected_file))
            current = _CommitAccumulator.from_header(line)
            continue

        if current is not None and line.strip():
            changed_path = _path_from_numstat(line)
            if changed_path is not None:
                current.changed_files.add(changed_path)

    if current is not None:
        commits.append(current.to_summary(selected_file))
    return tuple(commits)


def parse_commit_detail(raw: str) -> GitCommitDetail:
    lines = raw.splitlines()
    if not lines:
        raise GitClientError("git show returned no commit detail.")

    header = lines[0].split(FIELD_SEP, maxsplit=5)
    if len(header) != 6:
        raise GitClientError("git show returned an unexpected commit detail header.")

    commit_hash, short_hash, date_text, author, message, first_body_line = header
    body_lines: list[str] = []
    changed_files: list[str] = []
    in_files = False

    if first_body_line:
        body_lines.append(first_body_line)

    for line in lines[1:]:
        if not in_files and line == "":
            in_files = True
            continue
        if in_files:
            if line:
                changed_files.append(line)
        else:
            body_lines.append(line)

    return GitCommitDetail(
        commit_hash=commit_hash,
        short_hash=short_hash,
        date=datetime.fromisoformat(date_text),
        author=author,
        message=message,
        changed_files_count=len(changed_files),
        changed_files=tuple(changed_files),
        body="\n".join(body_lines).strip(),
    )


class _CommitAccumulator:
    def __init__(self, commit_hash: str, short_hash: str, date: datetime, author: str, message: str) -> None:
        self.commit_hash = commit_hash
        self.short_hash = short_hash
        self.date = date
        self.author = author
        self.message = message
        self.changed_files: set[str] = set()

    @classmethod
    def from_header(cls, line: str) -> "_CommitAccumulator":
        parts = line.split(FIELD_SEP)
        if len(parts) != 5:
            raise GitClientError("git log returned an unexpected commit header.")
        commit_hash, short_hash, date_text, author, message = parts
        return cls(
            commit_hash=commit_hash,
            short_hash=short_hash,
            date=datetime.fromisoformat(date_text),
            author=author,
            message=message,
        )

    def to_summary(self, selected_file: str | None) -> GitCommitSummary:
        return GitCommitSummary(
            commit_hash=self.commit_hash,
            short_hash=self.short_hash,
            date=self.date,
            author=self.author,
            message=self.message,
            changed_files_count=len(self.changed_files),
            selected_file_touched=selected_file in self.changed_files if selected_file else False,
        )


def _path_from_numstat(line: str) -> str | None:
    parts = line.split("\t")
    if len(parts) < 3:
        return None
    return _normalize_changed_path(parts[-1])


def _normalize_changed_path(path: str) -> str:
    if " => " not in path:
        return path
    # Git numstat rename output can be "src/{old => new}.py" or "old => new".
    if "{" in path and "}" in path:
        prefix, rest = path.split("{", 1)
        middle, suffix = rest.split("}", 1)
        return prefix + middle.split(" => ", 1)[-1] + suffix
    return path.split(" => ", 1)[-1]
