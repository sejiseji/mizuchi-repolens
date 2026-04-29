from __future__ import annotations

from mizuchi.contracts.models import EdgeKind, FileNode, FolderNode, ViewMode
from mizuchi.graph import (
    DependencyRelation,
    build_dependency_view,
    build_domain_placeholder_view,
    build_folder_view,
    build_render_index,
)


def test_build_folder_view_adds_containment_edges() -> None:
    nodes = (
        FolderNode(id="folder:.", path=""),
        FolderNode(id="folder:src", path="src", parent="folder:."),
        FileNode(id="file:src/app.py", path="src/app.py", folder="folder:src"),
    )

    graph = build_folder_view("project", nodes)

    assert graph.metadata["view"] == "folder"
    assert [edge.kind for edge in graph.edges] == [EdgeKind.FOLDER, EdgeKind.FOLDER]
    assert graph.edges[0].source == "folder:."
    assert graph.edges[0].target == "folder:src"
    assert graph.edges[1].source == "folder:src"
    assert graph.edges[1].target == "file:src/app.py"
    assert graph.edges[1].certainty == "confirmed"


def test_build_dependency_view_filters_unknown_nodes_and_normalizes_semantics() -> None:
    nodes = (
        FileNode(id="file:src/app.py", path="src/app.py", folder="folder:src"),
        FileNode(id="file:src/db.py", path="src/db.py", folder="folder:src"),
    )

    graph = build_dependency_view(
        "project",
        nodes,
        (
            DependencyRelation(
                source="file:src/app.py",
                target="file:src/db.py",
                certainty="Confirmed",
                relation_tags=("Imports", "imports"),
                weight=250,
            ),
            ("file:src/app.py", "file:missing.py"),
        ),
    )

    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.kind == EdgeKind.DEPENDENCY
    assert edge.certainty == "confirmed"
    assert edge.weight == 100.0
    assert edge.relation_tags == ("dependency", "imports")


def test_domain_placeholder_and_render_index_are_cached_view_friendly() -> None:
    nodes = (
        FileNode(id="file:a.py", path="a.py", folder="folder:."),
        FileNode(id="file:b.py", path="b.py", folder="folder:."),
    )

    graph = build_domain_placeholder_view("project", nodes, (("file:a.py", "file:b.py"),))
    index = build_render_index(graph)

    assert graph.metadata["view"] == "domain"
    assert graph.metadata["placeholder"] is True
    assert index.visible_edges_by_view[ViewMode.DOMAIN] == (graph.edges[0].id,)
    assert index.edge_index_by_relation_tag["domain"] == (graph.edges[0].id,)
