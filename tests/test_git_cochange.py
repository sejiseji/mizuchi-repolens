from __future__ import annotations

from datetime import datetime, timezone

from mizuchi.contracts.models import EdgeKind, FileNode, GitCommitDetail
from mizuchi.git.cochange import build_cochange_edges, build_git_cochange_graph


def test_build_cochange_edges_weights_pairs() -> None:
    commits = [
        _detail("a" * 40, "one", ("src/a.py", "src/b.py", "src/c.py")),
        _detail("b" * 40, "two", ("src/a.py", "src/b.py")),
    ]

    edges = build_cochange_edges(commits, min_weight=2)

    assert len(edges) == 1
    assert edges[0].source == "src/a.py"
    assert edges[0].target == "src/b.py"
    assert edges[0].kind == EdgeKind.CO_CHANGE
    assert edges[0].weight == 2.0
    assert edges[0].relation_tags == ("git", "co_change")


def test_build_git_cochange_graph_filters_to_known_file_nodes() -> None:
    commits = [_detail("a" * 40, "one", ("src/a.py", "src/b.py", "unknown.py"))]
    nodes = [FileNode(id="src/a.py", path="src/a.py", folder="src"), FileNode(id="src/b.py", path="src/b.py", folder="src")]

    graph = build_git_cochange_graph("project", commits, nodes)

    assert graph.project_hash == "project"
    assert graph.nodes == tuple(nodes)
    assert len(graph.edges) == 1
    assert graph.edges[0].source == "src/a.py"
    assert graph.edges[0].target == "src/b.py"
    assert graph.metadata["view"] == "git_cluster"


def _detail(commit_hash: str, message: str, files: tuple[str, ...]) -> GitCommitDetail:
    return GitCommitDetail(
        commit_hash=commit_hash,
        short_hash=commit_hash[:7],
        date=datetime.now(timezone.utc),
        author="Tester",
        message=message,
        changed_files_count=len(files),
        changed_files=files,
    )
