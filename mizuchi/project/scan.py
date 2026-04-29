"""Quick graph scan builder for inventory data."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from mizuchi.contracts.models import FileNode, FolderNode, GraphData
from mizuchi.project.inventory import ProjectInventory, scan_project_inventory
from mizuchi.project.validation import validate_project_root


def build_quick_scan_graph(project_root: str | Path, *, max_files: int | None = None) -> GraphData:
    """Validate a project and return a lightweight folder/file graph payload."""

    root = validate_project_root(project_root)
    inventory = scan_project_inventory(root.path, max_files=max_files)
    return graph_from_inventory(root.project_hash, inventory)


def graph_from_inventory(project_hash: str, inventory: ProjectInventory) -> GraphData:
    folder_nodes = tuple(
        FolderNode(
            id=_folder_id(folder.path),
            path=folder.path,
            parent=_folder_id(folder.parent) if folder.parent is not None else None,
            capture_children=folder.capture_children,
            collapsed=folder.collapsed,
            child_count=folder.child_count,
            visible_child_count=folder.visible_child_count,
            volatile=folder.volatile,
        )
        for folder in inventory.folders
    )
    file_nodes = tuple(
        FileNode(
            id=_file_id(file.path),
            path=file.path,
            folder=_folder_id(file.folder),
            language=file.language,
        )
        for file in inventory.files
    )
    return GraphData(
        project_hash=project_hash,
        generated_at=datetime.now(timezone.utc),
        nodes=folder_nodes + file_nodes,
        metadata={
            "scan": "quick",
            "file_count": len(file_nodes),
            "folder_count": len(folder_nodes),
            "read_only": True,
        },
    )


def _file_id(path: str) -> str:
    return f"file:{path}"


def _folder_id(path: str | None) -> str:
    return f"folder:{path or '.'}"
