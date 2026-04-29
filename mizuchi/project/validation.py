"""Read-only project root validation."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from mizuchi.contracts.models import ProjectRoot


class ProjectRootError(ValueError):
    """Raised when a project root cannot be opened safely."""


def validate_project_root(path: str | Path) -> ProjectRoot:
    """Validate and identify a project root using read-only filesystem checks."""

    raw_path = Path(path).expanduser()
    try:
        resolved = raw_path.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ProjectRootError(f"project root does not exist: {raw_path}") from exc

    if not resolved.is_dir():
        raise ProjectRootError(f"project root is not a directory: {resolved}")

    display_name = resolved.name or resolved.anchor
    digest = sha256(str(resolved).encode("utf-8")).hexdigest()[:16]
    return ProjectRoot(
        path=resolved,
        display_name=display_name,
        project_hash=digest,
        is_git_repo=(resolved / ".git").exists(),
        opened_at=datetime.now(timezone.utc),
    )
