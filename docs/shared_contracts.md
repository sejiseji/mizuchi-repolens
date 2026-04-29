# Mizuchi RepoLens Shared Contracts

These contracts are Manager-owned. Workers may import them but must not change them without reporting back to the Manager.

## Model Ownership

Source: `mizuchi/contracts/models.py`

| Contract | Purpose | Initial Owner |
|---|---|---|
| `ProjectRoot` | Opened project identity; target repository remains read-only. | Manager |
| `CachePath` | Standalone cache directory outside the target repository. | Manager |
| `FileNode` | File graph node with FileInsight role/summary metadata. | Manager |
| `FolderNode` | Folder graph node and capture policy metadata. | Manager |
| `EvidenceRef` | Source reference for evidence, edges, and future issue details. | Manager |
| `Edge` | Semantic relation with direction, certainty, weight, and evidence refs. | Manager |
| `GraphData` | Complete graph payload for UI and cached artifacts. | Manager |
| `LayoutCache` | View-mode layout positions plus invalidation manifest. | Manager |
| `EdgeRouteSet` | Routed edge ports and path points. | Manager |
| `RenderIndex` | Precomputed render indexes for view, relation, and encoding switches. | Manager |
| `GitCommitSummary` | Timeline row payload. | Manager |
| `GitCommitDetail` | Commit detail payload and changed files. | Manager |
| `DiffResult` | Truncated read-only diff payload. | Manager |
| `ApiResponse` / `ApiError` | Common API response envelope. | Manager |

## Stability Rules

- Contracts must not require Kuchinawa runtime state, artifacts, or `PROJECT_ROOT`.
- Contracts must not include CommandCenter, Task/Campaign, Codex execution, patch, Sheets, or runtime-loop concepts.
- Paths in API and graph payloads are project-relative unless explicitly documented as cache paths.
- Target repository paths are read-only.
- Cache paths are owned by Mizuchi and must live outside the opened repository by default.
- Git payloads are derived only from read-only commands: `git log`, `git show`, and `git diff`.

## Worker Dependency Notes

- Worker A consumes `ProjectRoot`, `CachePath`, `ApiResponse`, and `ApiError`.
- Worker B consumes `ProjectRoot`, `CachePath`, `FileNode`, `FolderNode`, `EvidenceRef`, and `GraphData`.
- Worker C consumes `FileNode`, `FolderNode`, `Edge`, `GraphData`, `LayoutCache`, `EdgeRouteSet`, and `RenderIndex`.
- Worker D consumes `ProjectRoot`, `GitCommitSummary`, `GitCommitDetail`, `DiffResult`, `Edge`, and `GraphData`.
