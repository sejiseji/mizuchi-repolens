"""Render index builders for graph view and relation lookups."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from mizuchi.contracts.models import Edge, EdgeKind, GraphData, RenderIndex, ViewMode


VIEW_EDGE_KINDS: dict[ViewMode, frozenset[EdgeKind]] = {
    ViewMode.ROLE: frozenset(
        {
            EdgeKind.FOLDER,
            EdgeKind.DEPENDENCY,
            EdgeKind.CO_CHANGE,
            EdgeKind.DOMAIN,
            EdgeKind.ISSUE,
        }
    ),
    ViewMode.FOLDER: frozenset({EdgeKind.FOLDER}),
    ViewMode.DEPENDENCY: frozenset({EdgeKind.DEPENDENCY}),
    ViewMode.GIT_CLUSTER: frozenset({EdgeKind.CO_CHANGE}),
    ViewMode.DOMAIN: frozenset({EdgeKind.DOMAIN}),
}


def build_render_index(graph: GraphData) -> RenderIndex:
    """Precompute edge IDs by view mode and relation tag."""

    return RenderIndex(
        visible_edges_by_view=_visible_edges_by_view(graph.edges),
        edge_index_by_relation_tag=_edge_index_by_relation_tag(graph.edges),
        style_tokens_by_encoding=_default_style_tokens(),
    )


def visible_edge_ids_for_view(edges: Iterable[Edge], view_mode: ViewMode) -> tuple[str, ...]:
    allowed = VIEW_EDGE_KINDS[view_mode]
    return tuple(edge.id for edge in edges if edge.kind in allowed)


def _visible_edges_by_view(edges: tuple[Edge, ...]) -> dict[ViewMode, tuple[str, ...]]:
    return {view: visible_edge_ids_for_view(edges, view) for view in VIEW_EDGE_KINDS}


def _edge_index_by_relation_tag(edges: Iterable[Edge]) -> dict[str, tuple[str, ...]]:
    index: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        for tag in edge.relation_tags:
            index[tag].append(edge.id)
    return {tag: tuple(edge_ids) for tag, edge_ids in sorted(index.items())}


def _default_style_tokens() -> dict[str, dict[str, str]]:
    return {
        "certainty": {
            "confirmed": "edge-certainty-confirmed",
            "inferred": "edge-certainty-inferred",
            "candidate": "edge-certainty-candidate",
        },
        "direction": {
            "directed": "edge-direction-directed",
            "undirected": "edge-direction-undirected",
        },
        "weight": {
            "light": "edge-weight-light",
            "normal": "edge-weight-normal",
            "heavy": "edge-weight-heavy",
        },
    }
