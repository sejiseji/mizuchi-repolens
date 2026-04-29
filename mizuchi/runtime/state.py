"""In-memory runtime state for the standalone server."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from mizuchi.contracts.models import CachePath, ProjectRoot
from mizuchi.runtime.project import open_project
from mizuchi.storage.cache import resolve_cache_path


@dataclass
class RuntimeState:
    """Mutable state owned by one local Mizuchi runtime."""

    current_project: ProjectRoot | None = None
    cache_path: CachePath | None = None

    def open_project(self, path: str | Path, cache_root: Path | None = None) -> ProjectRoot:
        project = open_project(path)
        self.cache_path = resolve_cache_path(project.path, project.project_hash, cache_root=cache_root)
        self.current_project = project
        return project

    def current_project_json(self) -> dict[str, object] | None:
        if self.current_project is None:
            return None

        data: dict[str, object] = {"project": self.current_project.as_json()}
        if self.cache_path is not None:
            data["cache"] = self.cache_path.as_json()
        return data
