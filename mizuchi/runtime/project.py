"""Read-only project opening helpers."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from mizuchi.contracts.models import ProjectRoot


class ProjectOpenError(ValueError):
    """Raised when a project root cannot be opened safely."""


def project_hash_for_path(path: Path) -> str:
    normalized = str(path.expanduser().resolve())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def open_project(path: str | Path) -> ProjectRoot:
    """Open a repository root for read-only inspection."""

    root = Path(path).expanduser().resolve()
    if not root.exists():
        raise ProjectOpenError("project path does not exist")
    if not root.is_dir():
        raise ProjectOpenError("project path must be a directory")

    return ProjectRoot(
        path=root,
        display_name=root.name,
        project_hash=project_hash_for_path(root),
        is_git_repo=(root / ".git").exists(),
        opened_at=datetime.now(timezone.utc),
    )
