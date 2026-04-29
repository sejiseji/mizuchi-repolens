"""Cache path resolution for Mizuchi-owned artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from mizuchi.contracts.models import CachePath


class CachePathError(ValueError):
    """Raised when a cache path would violate storage isolation."""


NAMESPACE = "mizuchi-repolens"
QUICK_SCAN_DIR = "quick_scan"
QUICK_SCAN_ARTIFACTS = frozenset(
    {
        "quick_scan",
        "file_inventory",
        "file_insights",
        "files_tree",
        "graph_data",
        "graph_layouts",
        "graph_render_index",
        "graph_edge_routes",
    }
)


def default_cache_root() -> Path:
    """Return the default Mizuchi cache namespace root."""

    override = os.environ.get("MIZUCHI_CACHE_HOME")
    if override:
        return Path(override).expanduser()

    xdg_cache_home = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache_home:
        return Path(xdg_cache_home).expanduser() / NAMESPACE

    return Path.home() / ".cache" / NAMESPACE


def resolve_cache_path(project_root: Path, project_hash: str, cache_root: Path | None = None) -> CachePath:
    """Resolve a cache path outside the opened target repository."""

    target_root = project_root.expanduser().resolve()
    root = (cache_root or default_cache_root()).expanduser().resolve()

    if root == target_root or target_root in root.parents:
        raise CachePathError("cache root must be outside the target repository")

    return CachePath(root=root, project_hash=project_hash)


def quick_scan_artifact_path(cache_path: CachePath, artifact_name: str) -> Path:
    """Return a whitelisted Quick Scan artifact path under Mizuchi cache."""

    if artifact_name not in QUICK_SCAN_ARTIFACTS:
        raise CachePathError(f"unknown quick scan artifact: {artifact_name}")
    return cache_path.project_dir / QUICK_SCAN_DIR / f"{artifact_name}.json"


def read_quick_scan_artifact(cache_path: CachePath, artifact_name: str) -> dict[str, Any] | None:
    """Read a Quick Scan JSON artifact from the Mizuchi cache if it exists."""

    path = quick_scan_artifact_path(cache_path, artifact_name)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise CachePathError(f"quick scan artifact is not a JSON object: {artifact_name}")
    return data


def write_quick_scan_artifact(cache_path: CachePath, artifact_name: str, payload: dict[str, Any]) -> Path:
    """Write a Quick Scan JSON artifact inside the Mizuchi cache namespace."""

    path = quick_scan_artifact_path(cache_path, artifact_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")
    return path
