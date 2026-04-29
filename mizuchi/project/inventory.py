"""Read-only file inventory for RepoLens quick scans."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any, Iterable

from mizuchi.project.paths import safe_project_relative_path


PROJECT_INVENTORY_SCHEMA_VERSION = "mizuchi_project_inventory_v0_2"

DEFAULT_VOLATILE_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "coverage",
        "dist",
        "node_modules",
        "target",
        "vendor",
    }
)

LANGUAGE_BY_SUFFIX = {
    ".c": "C",
    ".cc": "C++",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".json": "JSON",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".m": "Objective-C",
    ".md": "Markdown",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".sh": "Shell",
    ".swift": "Swift",
    ".toml": "TOML",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".yaml": "YAML",
    ".yml": "YAML",
}


@dataclass(frozen=True)
class FolderCaptureDecision:
    capture_children: bool
    collapsed: bool = False
    volatile: bool = False


@dataclass(frozen=True)
class FolderPolicy:
    volatile_dir_names: frozenset[str] = DEFAULT_VOLATILE_DIR_NAMES
    collapse_volatile: bool = True
    follow_symlink_dirs: bool = False

    def decide(self, relative_path: str) -> FolderCaptureDecision:
        name = Path(relative_path).name if relative_path else ""
        if name in self.volatile_dir_names:
            return FolderCaptureDecision(
                capture_children=False,
                collapsed=self.collapse_volatile,
                volatile=True,
            )
        return FolderCaptureDecision(capture_children=True)


DEFAULT_FOLDER_POLICY = FolderPolicy()


@dataclass(frozen=True)
class FileInventoryEntry:
    path: str
    folder: str
    language: str | None
    size_bytes: int
    is_symlink: bool = False


@dataclass(frozen=True)
class FolderInventoryEntry:
    path: str
    parent: str | None
    capture_children: bool = True
    collapsed: bool = False
    child_count: int = 0
    visible_child_count: int = 0
    volatile: bool = False


@dataclass(frozen=True)
class ProjectInventory:
    root: Path
    files: tuple[FileInventoryEntry, ...] = field(default_factory=tuple)
    folders: tuple[FolderInventoryEntry, ...] = field(default_factory=tuple)


def inventory_to_payload(inventory: ProjectInventory) -> dict[str, Any]:
    """Return a JSON-ready, deterministic inventory payload for cache writers."""

    return {
        "schema_version": PROJECT_INVENTORY_SCHEMA_VERSION,
        "project_root": str(inventory.root),
        "file_count": len(inventory.files),
        "folder_count": len(inventory.folders),
        "files": [file_inventory_entry_to_payload(file) for file in inventory.files],
        "folders": [folder_inventory_entry_to_payload(folder) for folder in inventory.folders],
    }


def file_inventory_entry_to_payload(entry: FileInventoryEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "folder": entry.folder,
        "language": entry.language,
        "size_bytes": entry.size_bytes,
        "is_symlink": entry.is_symlink,
        "path_tokens": list(path_tokens(entry.path)),
    }


def folder_inventory_entry_to_payload(entry: FolderInventoryEntry) -> dict[str, Any]:
    return {
        "path": entry.path,
        "parent": entry.parent,
        "capture_children": entry.capture_children,
        "collapsed": entry.collapsed,
        "child_count": entry.child_count,
        "visible_child_count": entry.visible_child_count,
        "volatile": entry.volatile,
    }


def path_tokens(relative_path: str, *, limit: int = 16) -> tuple[str, ...]:
    """Return stable tokens derived from a project-relative path."""

    parts = [part for part in relative_path.replace("\\", "/").split("/") if part]
    stem = Path(relative_path).stem
    tokens: list[str] = []
    for part in parts:
        part_path = Path(part)
        _append_token(tokens, part_path.stem if part_path.suffix else part)
    for chunk in stem.replace("-", "_").split("_"):
        _append_token(tokens, chunk)
    return tuple(tokens[:limit])


def scan_project_inventory(
    project_root: str | Path,
    *,
    folder_policy: FolderPolicy = DEFAULT_FOLDER_POLICY,
    max_files: int | None = None,
) -> ProjectInventory:
    """Build a read-only inventory of files and folders under ``project_root``."""

    root = Path(project_root).expanduser().resolve(strict=True)
    files: list[FileInventoryEntry] = []
    folders_by_path: dict[str, FolderInventoryEntry] = {}
    child_counts: dict[str, int] = {}
    visible_child_counts: dict[str, int] = {}

    def remember_folder(path: Path, decision: FolderCaptureDecision | None = None) -> str:
        relative = safe_project_relative_path(root, path)
        parent = _parent_path(relative)
        if relative not in folders_by_path:
            effective_decision = decision or folder_policy.decide(relative)
            folders_by_path[relative] = FolderInventoryEntry(
                path=relative,
                parent=parent,
                capture_children=effective_decision.capture_children,
                collapsed=effective_decision.collapsed,
                volatile=effective_decision.volatile,
            )
        return relative

    remember_folder(root, FolderCaptureDecision(capture_children=True))

    for current, dir_names, file_names in _walk_project(root, folder_policy=folder_policy):
        current_path = Path(current)
        current_relative = remember_folder(current_path)

        captured_dirs: list[str] = []
        for dir_name in sorted(dir_names):
            dir_path = current_path / dir_name
            relative = safe_project_relative_path(root, dir_path)
            decision = folder_policy.decide(relative)
            remember_folder(dir_path, decision)
            _increment(child_counts, current_relative)
            if decision.capture_children:
                _increment(visible_child_counts, current_relative)
                captured_dirs.append(dir_name)
        dir_names[:] = captured_dirs

        for file_name in sorted(file_names):
            file_path = current_path / file_name
            relative = safe_project_relative_path(root, file_path)
            try:
                stat_result = file_path.lstat()
            except OSError:
                continue
            files.append(
                FileInventoryEntry(
                    path=relative,
                    folder=current_relative,
                    language=detect_language(file_path),
                    size_bytes=stat_result.st_size,
                    is_symlink=file_path.is_symlink(),
                )
            )
            _increment(child_counts, current_relative)
            _increment(visible_child_counts, current_relative)
            if max_files is not None and len(files) >= max_files:
                return _finalize_inventory(root, files, folders_by_path, child_counts, visible_child_counts)

    return _finalize_inventory(root, files, folders_by_path, child_counts, visible_child_counts)


def detect_language(path: Path) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower())


def _append_token(tokens: list[str], value: str) -> None:
    lowered = value.lower().strip()
    if lowered and lowered not in tokens:
        tokens.append(lowered)


def _walk_project(root: Path, *, folder_policy: FolderPolicy) -> Iterable[tuple[str, list[str], list[str]]]:
    return os.walk(root, topdown=True, followlinks=folder_policy.follow_symlink_dirs)


def _parent_path(relative_path: str) -> str | None:
    if not relative_path:
        return None
    parent = Path(relative_path).parent.as_posix()
    return "" if parent == "." else parent


def _increment(counts: dict[str, int], key: str) -> None:
    counts[key] = counts.get(key, 0) + 1


def _finalize_inventory(
    root: Path,
    files: list[FileInventoryEntry],
    folders_by_path: dict[str, FolderInventoryEntry],
    child_counts: dict[str, int],
    visible_child_counts: dict[str, int],
) -> ProjectInventory:
    folders = tuple(
        FolderInventoryEntry(
            path=folder.path,
            parent=folder.parent,
            capture_children=folder.capture_children,
            collapsed=folder.collapsed,
            child_count=child_counts.get(folder.path, 0),
            visible_child_count=visible_child_counts.get(folder.path, 0),
            volatile=folder.volatile,
        )
        for folder in sorted(folders_by_path.values(), key=lambda item: (item.path.count("/"), item.path))
    )
    return ProjectInventory(root=root, files=tuple(files), folders=folders)
