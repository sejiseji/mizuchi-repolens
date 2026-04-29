"""Port selection and preview edge route helpers."""

from __future__ import annotations

from hashlib import sha256

from mizuchi.contracts.models import (
    Edge,
    EdgeRoute,
    EdgeRoutePoint,
    EdgeRouteSet,
    EdgeRoutingLevel,
    FileNode,
    FolderNode,
    LayoutPosition,
)


def preferred_port_count(node: FileNode | FolderNode) -> int:
    """Use 16 ports for most nodes and 24 for high-degree or folder nodes."""

    if isinstance(node, FolderNode):
        return 24
    return 24 if node.degree >= 16 or node.port_count == 24 else 16


def select_edge_port(edge: Edge, node_id: str, port_count: int) -> int:
    """Select a deterministic 16/24-compatible port index for an edge endpoint."""

    if port_count not in (16, 24):
        raise ValueError("port_count must be 16 or 24")
    endpoint = "source" if edge.source == node_id else "target"
    digest = sha256(f"{edge.id}:{node_id}:{endpoint}".encode("utf-8")).digest()
    return int.from_bytes(digest[:2], "big") % port_count


def build_edge_routes(
    edges: tuple[Edge, ...],
    positions: tuple[LayoutPosition, ...],
    nodes: tuple[FileNode | FolderNode, ...] = (),
    *,
    routing_level: EdgeRoutingLevel = EdgeRoutingLevel.PREVIEW,
) -> EdgeRouteSet:
    """Build placeholder polyline routes for edges with known endpoint positions."""

    by_position = {position.node_id: position for position in positions}
    by_node = {node.id: node for node in nodes}
    routes: list[EdgeRoute] = []
    for edge in edges:
        source = by_position.get(edge.source)
        target = by_position.get(edge.target)
        if source is None or target is None:
            continue
        source_port_count = preferred_port_count(by_node[edge.source]) if edge.source in by_node else 16
        target_port_count = preferred_port_count(by_node[edge.target]) if edge.target in by_node else 16
        routes.append(
            EdgeRoute(
                edge_id=edge.id,
                source_port=select_edge_port(edge, edge.source, source_port_count),
                target_port=select_edge_port(edge, edge.target, target_port_count),
                points=_placeholder_points(source, target),
                routing_level=routing_level,
            )
        )
    return EdgeRouteSet(routes=tuple(routes))


def _placeholder_points(source: LayoutPosition, target: LayoutPosition) -> tuple[EdgeRoutePoint, ...]:
    start = _center(source)
    end = _center(target)
    midpoint_x = (start.x + end.x) / 2
    return (
        start,
        EdgeRoutePoint(x=midpoint_x, y=start.y),
        EdgeRoutePoint(x=midpoint_x, y=end.y),
        end,
    )


def _center(position: LayoutPosition) -> EdgeRoutePoint:
    return EdgeRoutePoint(
        x=position.x + ((position.width or 0.0) / 2),
        y=position.y + ((position.height or 0.0) / 2),
    )
