"""Co-change edge builders backed by git timeline details."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from itertools import combinations

from mizuchi.contracts.models import Edge, EdgeDirection, EdgeKind, EvidenceRef, FileNode, GraphData, GitCommitDetail


def build_cochange_edges(
    commits: Iterable[GitCommitDetail],
    known_node_ids: Iterable[str] | None = None,
    min_weight: int = 1,
) -> tuple[Edge, ...]:
    """Build undirected co-change edges between files changed in the same commits."""

    allowed = set(known_node_ids) if known_node_ids is not None else None
    pair_weights: dict[tuple[str, str], int] = defaultdict(int)
    pair_evidence: dict[tuple[str, str], list[EvidenceRef]] = defaultdict(list)

    for commit in commits:
        files = sorted(_eligible_files(commit.changed_files, allowed))
        for source, target in combinations(files, 2):
            pair = (source, target)
            pair_weights[pair] += 1
            pair_evidence[pair].append(
                EvidenceRef(
                    file=source,
                    kind="git_commit",
                    text=f"{commit.short_hash} {commit.message}",
                )
            )

    edges: list[Edge] = []
    for (source, target), weight in sorted(pair_weights.items()):
        if weight < min_weight:
            continue
        edge_id = f"cochange:{source}:{target}"
        edges.append(
            Edge(
                id=edge_id,
                source=source,
                target=target,
                kind=EdgeKind.CO_CHANGE,
                direction=EdgeDirection.UNDIRECTED,
                certainty="inferred",
                weight=float(weight),
                relation_tags=("git", "co_change"),
                evidence_level="commit_history",
                label="co-change",
                detail_label=f"changed together {weight} time{'s' if weight != 1 else ''}",
                evidence_refs=tuple(pair_evidence[(source, target)][:5]),
            )
        )
    return tuple(edges)


def build_git_cochange_graph(
    project_hash: str,
    commits: Iterable[GitCommitDetail],
    file_nodes: Iterable[FileNode],
    min_weight: int = 1,
) -> GraphData:
    """Return a GraphData slice containing file nodes and git co-change edges."""

    nodes = tuple(file_nodes)
    edges = build_cochange_edges(
        commits=commits,
        known_node_ids=(node.id for node in nodes),
        min_weight=min_weight,
    )
    return GraphData(
        project_hash=project_hash,
        generated_at=datetime.now(timezone.utc),
        nodes=nodes,
        edges=edges,
        metadata={"view": "git_cluster", "edge_kind": EdgeKind.CO_CHANGE.value},
    )


def _eligible_files(paths: Iterable[str], allowed: set[str] | None) -> set[str]:
    files = {path for path in paths if path and not path.endswith("/")}
    if allowed is None:
        return files
    return files.intersection(allowed)
