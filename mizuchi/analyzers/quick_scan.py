"""Quick scan analyzer composing inventory and fallback FileInsight data."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mizuchi.contracts.models import FileNode, GraphData, SummaryStatus
from mizuchi.insight.adapters import (
    FallbackFileInsightAdapter,
    FileInsightAdapter,
    FileInsightResult,
    file_insight_result_to_payload,
)
from mizuchi.project.inventory import inventory_to_payload, scan_project_inventory
from mizuchi.project.scan import graph_from_inventory
from mizuchi.project.validation import validate_project_root


QUICK_SCAN_PAYLOAD_SCHEMA_VERSION = "mizuchi_quick_scan_v0_2"


@dataclass(frozen=True)
class QuickScanResult:
    graph: GraphData
    insights: tuple[FileInsightResult, ...]
    inventory: dict[str, Any] | None = None


def quick_scan_project(
    project_root: str | Path,
    *,
    insight_adapter: FileInsightAdapter | None = None,
    max_files: int | None = None,
) -> QuickScanResult:
    """Run the read-only inventory scan and attach fallback FileInsight facets."""

    root = validate_project_root(project_root)
    inventory = scan_project_inventory(root.path, max_files=max_files)
    graph = graph_from_inventory(root.project_hash, inventory)
    adapter = insight_adapter or FallbackFileInsightAdapter()
    insights = tuple(
        adapter.inspect_file(root.path, node.path)
        for node in graph.nodes
        if isinstance(node, FileNode)
    )
    return QuickScanResult(
        graph=_apply_insight_metadata(graph, insights),
        insights=insights,
        inventory=inventory_to_payload(inventory),
    )


def quick_scan_result_to_payload(result: QuickScanResult) -> dict[str, Any]:
    """Return a JSON-ready quick scan payload for Mizuchi cache/API layers."""

    return {
        "schema_version": QUICK_SCAN_PAYLOAD_SCHEMA_VERSION,
        "graph": result.graph.as_json(),
        "inventory": result.inventory,
        "insights": [file_insight_result_to_payload(insight) for insight in result.insights],
    }


def _apply_insight_metadata(graph: GraphData, insights: tuple[FileInsightResult, ...]) -> GraphData:
    by_path = {insight.path: insight for insight in insights}
    nodes = tuple(
        _file_node_with_insight(node, by_path.get(node.path))
        if isinstance(node, FileNode)
        else node
        for node in graph.nodes
    )
    return GraphData(
        project_hash=graph.project_hash,
        generated_at=graph.generated_at,
        nodes=nodes,
        edges=graph.edges,
        metadata={**graph.metadata, "insight_adapter": "fallback"},
    )


def _file_node_with_insight(node: FileNode, insight: FileInsightResult | None) -> FileNode:
    role = insight.role if insight is not None else None
    summary = insight.summary if insight is not None else None
    return FileNode(
        id=node.id,
        path=node.path,
        folder=node.folder,
        language=node.language,
        role=role.role if role is not None else "unknown",
        role_confidence=role.confidence if role is not None else 0.0,
        summary_status=summary.status if summary is not None else SummaryStatus.MISSING,
        issue_count=len(insight.issues) if insight is not None else 0,
        degree=node.degree,
        port_count=node.port_count,
        last_modified_commit=node.last_modified_commit,
    )
