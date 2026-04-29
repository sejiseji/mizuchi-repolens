"""Helpers for safe, project-relative path handling.

These functions are intentionally about resolution and validation only. They do
not create, modify, or delete files in the opened project.
"""

from __future__ import annotations

from pathlib import Path


class PathSafetyError(ValueError):
    """Raised when a path cannot be safely treated as project-relative."""


def _reject_suspicious_text(value: str) -> None:
    if "\x00" in value:
        raise PathSafetyError("path contains a null byte")


def resolve_project_path(project_root: Path, relative_path: str | Path) -> Path:
    """Resolve a project-relative path without allowing escape from the root."""

    root = project_root.expanduser().resolve()
    requested = Path(relative_path)
    requested_text = str(relative_path)
    _reject_suspicious_text(requested_text)

    if requested.is_absolute():
        raise PathSafetyError("absolute paths are not allowed")

    resolved = (root / requested).resolve()
    if resolved != root and root not in resolved.parents:
        raise PathSafetyError("path escapes the project root")
    return resolved


def project_relative_path(project_root: Path, candidate: str | Path) -> str:
    """Return a normalized POSIX project-relative path for a safe candidate."""

    root = project_root.expanduser().resolve()
    candidate_path = Path(candidate)
    _reject_suspicious_text(str(candidate))
    resolved = candidate_path.expanduser().resolve() if candidate_path.is_absolute() else resolve_project_path(root, candidate_path)

    if resolved == root:
        return "."
    if root not in resolved.parents:
        raise PathSafetyError("path is outside the project root")
    return resolved.relative_to(root).as_posix()
