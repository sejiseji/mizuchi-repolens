from __future__ import annotations

from mizuchi.contracts.models import EdgeKind, EdgeRoutingLevel, FileNode, FolderNode, ViewMode
from mizuchi.graph import build_edge_routes, build_folder_view, build_layout_cache, preferred_port_count, select_edge_port


def test_layout_cache_contains_all_view_modes() -> None:
    graph = build_folder_view(
        "project",
        (
            FolderNode(id="folder:.", path=""),
            FileNode(id="file:a.py", path="a.py", folder="folder:."),
        ),
    )

    cache = build_layout_cache(graph)

    assert set(cache.layouts) == set(ViewMode)
    assert cache.manifest.project_graph_hash
    assert len(cache.layouts[ViewMode.FOLDER]) == 2


def test_port_selection_supports_16_and_24_port_nodes() -> None:
    graph = build_folder_view(
        "project",
        (
            FolderNode(id="folder:.", path=""),
            FileNode(id="file:a.py", path="a.py", folder="folder:."),
        ),
    )
    edge = graph.edges[0]

    assert edge.kind == EdgeKind.FOLDER
    assert preferred_port_count(graph.nodes[0]) == 24
    assert 0 <= select_edge_port(edge, edge.source, 16) < 16
    assert 0 <= select_edge_port(edge, edge.target, 24) < 24


def test_build_edge_routes_uses_layout_positions_without_scanning() -> None:
    graph = build_folder_view(
        "project",
        (
            FolderNode(id="folder:.", path=""),
            FileNode(id="file:a.py", path="a.py", folder="folder:."),
        ),
    )
    cache = build_layout_cache(graph)

    route_set = build_edge_routes(graph.edges, cache.layouts[ViewMode.FOLDER], graph.nodes)

    assert len(route_set.routes) == 1
    route = route_set.routes[0]
    assert route.routing_level == EdgeRoutingLevel.PREVIEW
    assert len(route.points) == 4
