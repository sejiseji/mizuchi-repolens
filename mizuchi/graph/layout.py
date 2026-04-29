"""Placeholder layout cache generation for graph view modes."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone
from hashlib import sha256
from math import ceil, sqrt

from mizuchi.contracts.models import (
    FileNode,
    FolderNode,
    GraphData,
    LayoutCache,
    LayoutManifest,
    LayoutPosition,
    ViewMode,
)


VIEW_MODES: tuple[ViewMode, ...] = (
    ViewMode.ROLE,
    ViewMode.FOLDER,
    ViewMode.DEPENDENCY,
    ViewMode.GIT_CLUSTER,
    ViewMode.DOMAIN,
)


def build_layout_cache(graph: GraphData) -> LayoutCache:
    """Create deterministic placeholder positions for every supported view."""

    graph_hash = graph_hash_for_layout(graph)
    layouts = {view: placeholder_layout(graph.nodes, view) for view in VIEW_MODES}
    return LayoutCache(
        layouts=layouts,
        manifest=LayoutManifest(
            project_graph_hash=graph_hash,
            folder_hash=graph_hash,
            dependency_hash=graph_hash,
            git_cochange_hash=graph_hash,
            role_hash=graph_hash,
            domain_probe_hash=graph_hash,
            computed_at=datetime.now(timezone.utc),
        ),
    )


def placeholder_layout(
    nodes: Iterable[FileNode | FolderNode],
    view_mode: ViewMode,
) -> tuple[LayoutPosition, ...]:
    """Return a stable grid layout placeholder for a view mode."""

    ordered = sorted(tuple(nodes), key=lambda node: (_kind_order(node), node.path, node.id))
    if not ordered:
        return ()
    columns = max(1, ceil(sqrt(len(ordered))))
    x_gap = 220.0 if view_mode is ViewMode.FOLDER else 180.0
    y_gap = 150.0 if view_mode is ViewMode.FOLDER else 120.0
    positions: list[LayoutPosition] = []
    for index, node in enumerate(ordered):
        row, column = divmod(index, columns)
        width = 180.0 if isinstance(node, FolderNode) else 132.0
        height = 96.0 if isinstance(node, FolderNode) else 72.0
        positions.append(
            LayoutPosition(
                node_id=node.id,
                x=column * x_gap,
                y=row * y_gap,
                width=width,
                height=height,
            )
        )
    return tuple(positions)


def graph_hash_for_layout(graph: GraphData) -> str:
    """Hash graph identity fields that affect placeholder layout invalidation."""

    digest = sha256()
    digest.update(graph.project_hash.encode("utf-8"))
    for node in sorted(graph.nodes, key=lambda item: item.id):
        digest.update(node.id.encode("utf-8"))
        digest.update(node.path.encode("utf-8"))
    for edge in sorted(graph.edges, key=lambda item: item.id):
        digest.update(edge.id.encode("utf-8"))
        digest.update(edge.source.encode("utf-8"))
        digest.update(edge.target.encode("utf-8"))
    return digest.hexdigest()[:16]


def _kind_order(node: FileNode | FolderNode) -> int:
    return 0 if isinstance(node, FolderNode) else 1
