"""Graph view builders that compose Manager-owned contracts."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone

from mizuchi.contracts.models import Edge, EdgeKind, EvidenceRef, FileNode, FolderNode, GraphData
from mizuchi.graph.semantics import (
    clamp_weight,
    direction_for_kind,
    evidence_level_for_refs,
    normalize_certainty,
    normalize_relation_tags,
    relation_tags_for_kind,
)


@dataclass(frozen=True)
class DependencyRelation:
    source: str
    target: str
    label: str | None = None
    weight: float = 1.0
    certainty: str = "candidate"
    relation_tags: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()


@dataclass(frozen=True)
class DomainRelation:
    source: str
    target: str
    label: str | None = None
    weight: float = 1.0
    certainty: str = "candidate"
    relation_tags: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()


def build_folder_view(project_hash: str, nodes: Iterable[FileNode | FolderNode]) -> GraphData:
    """Build a folder containment view from existing file and folder nodes."""

    node_tuple = tuple(nodes)
    edges = tuple(_folder_edges(node_tuple))
    return _graph(project_hash, node_tuple, edges, view="folder")


def build_dependency_view(
    project_hash: str,
    file_nodes: Iterable[FileNode],
    dependencies: Iterable[DependencyRelation | tuple[str, str]],
) -> GraphData:
    """Build a dependency view from file nodes and precomputed dependency facts."""

    nodes = tuple(file_nodes)
    allowed = {node.id for node in nodes}
    edges = tuple(
        edge
        for edge in (_dependency_edge(dep) for dep in dependencies)
        if edge.source in allowed and edge.target in allowed
    )
    return _graph(project_hash, nodes, edges, view="dependency")


def build_cochange_view(
    project_hash: str,
    file_nodes: Iterable[FileNode],
    cochange_edges: Iterable[Edge],
) -> GraphData:
    """Build a git-cluster graph slice from precomputed co-change edges."""

    nodes = tuple(file_nodes)
    allowed = {node.id for node in nodes}
    edges = tuple(
        edge
        for edge in cochange_edges
        if edge.kind is EdgeKind.CO_CHANGE and edge.source in allowed and edge.target in allowed
    )
    return _graph(project_hash, nodes, edges, view="git_cluster")


def build_domain_placeholder_view(
    project_hash: str,
    nodes: Iterable[FileNode | FolderNode],
    relations: Iterable[DomainRelation | tuple[str, str]] = (),
) -> GraphData:
    """Build a domain probe placeholder graph without requiring a domain scanner."""

    node_tuple = tuple(nodes)
    allowed = {node.id for node in node_tuple}
    edges = tuple(
        edge
        for edge in (_domain_edge(relation) for relation in relations)
        if edge.source in allowed and edge.target in allowed
    )
    graph = _graph(project_hash, node_tuple, edges, view="domain")
    return GraphData(
        project_hash=graph.project_hash,
        generated_at=graph.generated_at,
        nodes=graph.nodes,
        edges=graph.edges,
        metadata={**graph.metadata, "placeholder": True},
    )


def merge_graph_views(project_hash: str, graphs: Sequence[GraphData]) -> GraphData:
    """Merge cached graph slices into one renderable graph without rescanning."""

    nodes_by_id: dict[str, FileNode | FolderNode] = {}
    edges_by_id: dict[str, Edge] = {}
    views: list[str] = []
    for graph in graphs:
        view = graph.metadata.get("view")
        if isinstance(view, str):
            views.append(view)
        for node in graph.nodes:
            nodes_by_id.setdefault(node.id, node)
        for edge in graph.edges:
            edges_by_id.setdefault(edge.id, edge)

    return GraphData(
        project_hash=project_hash,
        generated_at=datetime.now(timezone.utc),
        nodes=tuple(nodes_by_id.values()),
        edges=tuple(edges_by_id.values()),
        metadata={"views": tuple(dict.fromkeys(views)), "source": "cached_graph_views"},
    )


def _folder_edges(nodes: tuple[FileNode | FolderNode, ...]) -> Iterable[Edge]:
    folders = {node.id for node in nodes if isinstance(node, FolderNode)}
    for node in nodes:
        if isinstance(node, FolderNode) and node.parent is not None and node.parent in folders:
            yield _make_edge(
                source=node.parent,
                target=node.id,
                kind=EdgeKind.FOLDER,
                certainty="confirmed",
                label="contains",
            )
        if isinstance(node, FileNode) and node.folder in folders:
            yield _make_edge(
                source=node.folder,
                target=node.id,
                kind=EdgeKind.FOLDER,
                certainty="confirmed",
                label="contains",
            )


def _dependency_edge(dep: DependencyRelation | tuple[str, str]) -> Edge:
    if isinstance(dep, DependencyRelation):
        return _make_edge(
            source=dep.source,
            target=dep.target,
            kind=EdgeKind.DEPENDENCY,
            certainty=dep.certainty,
            weight=dep.weight,
            label=dep.label or "depends on",
            extra_tags=dep.relation_tags,
            evidence_refs=dep.evidence_refs,
        )
    source, target = dep
    return _make_edge(source=source, target=target, kind=EdgeKind.DEPENDENCY, label="depends on")


def _domain_edge(relation: DomainRelation | tuple[str, str]) -> Edge:
    if isinstance(relation, DomainRelation):
        return _make_edge(
            source=relation.source,
            target=relation.target,
            kind=EdgeKind.DOMAIN,
            certainty=relation.certainty,
            weight=relation.weight,
            label=relation.label or "domain",
            extra_tags=relation.relation_tags,
            evidence_refs=relation.evidence_refs,
        )
    source, target = relation
    return _make_edge(source=source, target=target, kind=EdgeKind.DOMAIN, label="domain")


def _make_edge(
    *,
    source: str,
    target: str,
    kind: EdgeKind,
    certainty: str = "candidate",
    weight: float = 1.0,
    label: str | None = None,
    extra_tags: tuple[str, ...] = (),
    evidence_refs: tuple[EvidenceRef, ...] = (),
) -> Edge:
    relation_tags = normalize_relation_tags(relation_tags_for_kind(kind, *extra_tags))
    edge_id = f"{kind.value}:{source}:{target}"
    return Edge(
        id=edge_id,
        source=source,
        target=target,
        kind=kind,
        direction=direction_for_kind(kind),
        certainty=normalize_certainty(certainty),
        weight=clamp_weight(weight),
        relation_tags=relation_tags,
        evidence_level=evidence_level_for_refs(evidence_refs),
        label=label,
        evidence_refs=evidence_refs,
    )


def _graph(
    project_hash: str,
    nodes: tuple[FileNode | FolderNode, ...],
    edges: tuple[Edge, ...],
    *,
    view: str,
) -> GraphData:
    return GraphData(
        project_hash=project_hash,
        generated_at=datetime.now(timezone.utc),
        nodes=nodes,
        edges=edges,
        metadata={"view": view, "source": "graph_helpers"},
    )
