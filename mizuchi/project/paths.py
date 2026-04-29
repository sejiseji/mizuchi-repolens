"""Path safety helpers for read-only project inspection."""

from __future__ import annotations

from pathlib import Path


class ProjectPathError(ValueError):
    """Raised when a path cannot be represented safely within a project."""


def safe_project_relative_path(project_root: Path, candidate: Path) -> str:
    """Return a POSIX project-relative path after containment validation.

    The helper performs resolution only; it does not create, write, or mutate
    either path. A root-relative result of ``"."`` is returned as an empty
    string so graph payload paths remain project-relative.
    """

    root = project_root.expanduser().resolve(strict=True)
    path = candidate.expanduser().resolve(strict=False)
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ProjectPathError(f"path is outside project root: {candidate}") from exc

    relative_text = relative.as_posix()
    if relative_text == ".":
        return ""
    if relative_text.startswith("../") or relative_text == "..":
        raise ProjectPathError(f"path is outside project root: {candidate}")
    return relative_text
