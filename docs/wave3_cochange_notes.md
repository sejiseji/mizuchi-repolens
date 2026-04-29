# Wave 3 Git Co-change Integration Notes

Date: 2026-04-29

Worker: Worker C, Git co-change integration investigation

## Decision

Wave 3 can connect Git co-change without shared contract churn, but it should not wire the existing helper as-is.

Recommendation: connect in Wave 3 only after a small internal normalization step maps Git changed paths to existing `FileNode.id` values. If that implementation slot is not available in Wave 3, defer the connection and keep the current Git timeline/diff APIs plus graph folder view behavior.

No shared contract change is required.

## Findings

- Shared graph contracts already have the needed surface:
  - `ViewMode.GIT_CLUSTER = "git_cluster"`
  - `EdgeKind.CO_CHANGE = "co_change"`
  - `EdgeDirection.UNDIRECTED`
  - `LayoutManifest.git_cochange_hash`
  - `RenderIndex.visible_edges_by_view`
  - `GraphData.edges` and `Edge.evidence_refs`
- `mizuchi/git/cochange.py` already builds `EdgeKind.CO_CHANGE` edges with undirected direction, inferred certainty, weight, relation tags, evidence refs, and `GraphData.metadata["view"] == "git_cluster"`.
- `mizuchi/graph/builders.py` already has `build_cochange_view(project_hash, file_nodes, cochange_edges)` and filters to `EdgeKind.CO_CHANGE`.
- `mizuchi/graph/render_index.py` already maps `ViewMode.GIT_CLUSTER` to `EdgeKind.CO_CHANGE`.
- `mizuchi/graph/layout.py` already emits placeholder layouts for every `ViewMode`, including `GIT_CLUSTER`.
- Existing cache/API shape returns generic graph artifacts through:
  - `graph_data`
  - `graph_layouts`
  - `graph_render_index`
  - `graph_edge_routes`
  These can carry co-change edges without adding new response models.

## Main Integration Mismatch

The current co-change builder treats Git changed paths as graph node IDs:

- Git changed file: `src/app.py`
- Current scan `FileNode.id`: `file:src/app.py`
- Current scan `FileNode.path`: `src/app.py`

Because `build_git_cochange_graph()` passes `known_node_ids=(node.id for node in nodes)`, normal quick-scan nodes will not match raw Git paths. Direct integration would silently produce few or zero co-change edges for the real graph cache.

This is not a shared contract problem. The contract already separates `FileNode.id` and `FileNode.path`. The implementation should map commit `changed_files` paths to file-node IDs before building edges, or update the co-change helper internally to accept `FileNode` values and normalize paths through a `path -> node.id` lookup.

## Cache/API Fit

The lowest-churn Wave 3 integration path is:

1. During project rescan, keep the existing quick-scan graph as the source of nodes.
2. Build a `path -> FileNode.id` map from quick-scan file nodes.
3. Read recent Git commit details with changed files using the existing read-only Git wrappers.
4. Build co-change edges whose `source` and `target` are existing `FileNode.id` values.
5. Merge folder edges and co-change edges into the existing cached `graph_data`.
6. Rebuild existing `graph_layouts`, `graph_render_index`, and `graph_edge_routes` from that merged graph.

This keeps the public graph endpoint shape unchanged. The existing render index will expose Git-cluster visibility through `visible_edges_by_view["git_cluster"]`.

## Risks

- Direct use of `build_git_cochange_graph()` against current quick-scan nodes will likely produce no useful edges because of the path/id mismatch.
- Fetching changed files currently requires commit-detail data, while `/api/git/timeline` returns only summaries. A naive implementation may perform one `git show` per recent commit. That is acceptable for a small Wave 3 depth limit, but should be bounded and timeout-aware.
- Co-change edges can grow quadratically for commits touching many files. Integration should cap commit depth and skip or cap very large commits before creating pair combinations.
- Rename handling differs by source: timeline parsing normalizes rename paths from `--numstat`, but commit detail uses `git show --name-only --no-renames`. Wave 3 can accept this limitation if documented, but future work should normalize rename behavior consistently.
- Existing cache artifact names are quick-scan oriented. A separate `git/cochange_index.json` artifact is mentioned in the longer merge spec, but adding it is not necessary for Wave 3 if co-change is embedded in existing graph artifacts.

## Recommended Next Steps

1. Do not change shared contracts.
2. Add an implementation-only path normalization layer before co-change edges enter `GraphData`.
3. Use current `Edge`, `GraphData`, `ViewMode`, layout, render index, and route contracts as-is.
4. Keep the Wave 3 API surface unchanged unless Manager explicitly wants a separate diagnostics endpoint.
5. If connecting in Wave 3, add focused tests that prove co-change edges use `file:<path>` node IDs and appear in the render index under `git_cluster`.

## Manager Decision Requests

- Approve Wave 3 internal integration with no shared contract changes, provided path-to-node-ID normalization is included.
- Decide the initial Git history depth and large-commit cap for human testing.
- Decide whether co-change should be embedded only in existing graph artifacts for Wave 3, or whether a separate `git/cochange_index.json` cache artifact should be deferred to a later wave.
