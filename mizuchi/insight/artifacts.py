"""Cache artifact interfaces for insight outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mizuchi.contracts.models import CachePath


@dataclass(frozen=True)
class InsightArtifactRef:
    project_hash: str
    relative_path: str
    artifact_path: Path


class InsightArtifactStore(Protocol):
    def artifact_ref(self, relative_path: str) -> InsightArtifactRef:
        """Resolve the Mizuchi cache artifact location for a project file."""


class CacheInsightArtifactStore:
    """Resolve insight artifacts inside a Mizuchi-owned cache directory."""

    def __init__(self, cache_path: CachePath, *, project_root: Path | None = None) -> None:
        self.cache_path = cache_path
        self.project_root = project_root.resolve(strict=False) if project_root is not None else None
        if self.project_root is not None:
            cache_project_dir = cache_path.project_dir.resolve(strict=False)
            try:
                cache_project_dir.relative_to(self.project_root)
            except ValueError:
                pass
            else:
                raise ValueError("insight cache path must not live inside the opened project")

    def artifact_ref(self, relative_path: str) -> InsightArtifactRef:
        safe_path = _safe_artifact_relative_path(relative_path)
        return InsightArtifactRef(
            project_hash=self.cache_path.project_hash,
            relative_path=relative_path,
            artifact_path=self.cache_path.project_dir / "insight" / f"{safe_path}.json",
        )


def _safe_artifact_relative_path(relative_path: str) -> str:
    path = Path(relative_path)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe artifact path: {relative_path}")
    return "__root__" if relative_path == "" else relative_path.replace("/", "__")
