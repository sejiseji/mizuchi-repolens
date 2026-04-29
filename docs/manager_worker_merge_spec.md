# Mizuchi RepoLens Manager-Worker Merge Specification

## 0. Purpose

This specification defines how Mizuchi RepoLens work is managed across one Codex Manager session and up to four Worker sessions.

Basic model:

- Codex Main Session = Manager
  - TODO management
  - impact assessment
  - shared contract ownership
  - worker assignment
  - worker result review
  - integration decisions
  - final tests
  - reporting
- Worker Sessions = implementation owners
  - change only the assigned scope
  - do not change shared contracts without approval
  - preserve standalone/read-only boundaries
  - report results in the required format

Mizuchi RepoLens is a standalone/read-only repository analysis app. It must not carry Kuchinawa mainline features.

## 1. Project Premises

Project:

Mizuchi RepoLens

Working directory:

`<MIZUCHI_REPOLENS_ROOT>`

Mizuchi RepoLens has:

- arbitrary folder/repository opening
- self-contained scanning and analysis
- FileInsight-style functionality, safely adapted
- Dashboard/FileOverview concepts, safely adapted
- Git Timeline / Diff Viewer
- Graph View
- read-only behavior
- standalone launch and shutdown

Mizuchi RepoLens must not have:

- CommandCenter
- Task / Campaign
- Codex execution
- patch generation/application
- Sheets integration
- runtime loop
- planner/decomposition pipeline
- writes to the target repository

## 2. Roles

### 2.1 Manager Session

The Manager is the main Codex session.

Responsibilities:

1. Confirm current repository state.
2. Update `docs/manager_todo.md`.
3. Update `docs/worker_assignments.md`.
4. Own shared contracts.
5. Decompose worker tasks.
6. Write worker prompts.
7. Review worker outputs.
8. Detect conflicts.
9. Decide integration.
10. Run safety checks.
11. Run tests.
12. Produce final reports.

The Manager should avoid taking on large implementation slices directly. The Manager may directly handle:

- small shared contract edits
- docs updates
- light integration fixes
- import path / formatting / test adjustments
- removal of safety boundary violations

### 2.2 Worker Sessions

Workers implement only the limited scope assigned by the Manager.

Responsibilities:

1. Change only assigned files.
2. Do not change shared contracts without approval.
3. Avoid forbidden areas.
4. Preserve read-only / standalone boundaries.
5. Report changed files and implementation summary.
6. Report tests run or why tests were not run.
7. Request Manager decisions for shared contract changes.

Workers must not:

- change `docs/shared_contracts.md` without Manager approval
- change `mizuchi/contracts/models.py` without Manager approval
- change another worker's ownership area
- import CommandCenter / Task / Campaign code
- import Codex execution / patch / Sheets code
- add destructive Git commands
- use `shell=True`
- write to the target repository

## 3. Worker Count And Standard Slices

Maximum workers: 4

Default worker slices:

- Worker A: Runtime / API / Security / Storage
- Worker B: Project Inventory / FileInsight Adapter / Analyzer
- Worker C: Graph / Layout / Edge Semantics / Frontend Graph
- Worker D: Git Timeline / Commit Detail / Diff / Co-change

For UI-heavy waves, the Manager may reassign as:

- Worker A: API / Cache Integration
- Worker B: FileInsight / Project Inventory
- Worker C: Frontend Shell / Graph UI
- Worker D: Git / Smoke Test / Safety Test

## 4. Manager TODO Management

At the start of each wave, the Manager updates:

- `docs/manager_todo.md`
- `docs/worker_assignments.md`

As needed, the Manager may also update:

- `docs/shared_contracts.md`
- `docs/kuchinawa_reuse_notes.md`
- `docs/wave_notes.md`

TODOs should be scoped by worker, file scope, API, artifact, or test.

Good TODOs:

- Return `GET /api/files/tree` in `ApiResponse` shape.
- Save `graph_data.json` under the cache root.
- Show `/api/project/current` in the static shell.
- Return truncated large diffs from the Git diff API.

Avoid vague TODOs such as "build UI", "finish Git", or "integrate FileInsight".

## 5. Shared Contract Management

Manager-owned files:

- `mizuchi/contracts/models.py`
- `docs/shared_contracts.md`

Manager-owned shared contracts:

- `ProjectRoot`
- `CachePath`
- `FileNode`
- `FolderNode`
- `EvidenceRef`
- `Edge`
- `GraphData`
- `LayoutCache`
- `EdgeRouteSet`
- `RenderIndex`
- `GitCommitSummary`
- `GitCommitDetail`
- `DiffResult`
- `ApiResponse`
- `ApiError`

If a worker needs a shared contract change:

1. Worker does not edit it.
2. Worker reports the reason.
3. Worker proposes the change.
4. Manager reviews impact.
5. Manager accepts, rejects, or defers.
6. If accepted, Manager updates the contract.
7. Manager notifies all active workers.

Compatibility policy:

- Prefer backward-compatible changes.
- Usually acceptable: optional fields, defaults, reserved enum values, docstring clarification.
- Avoid: field renames, required fields, breaking type changes, breaking API response shape changes.

## 6. Worker Assignment Specification

Each worker assignment should include:

- Worker name
- Goal
- Allowed files
- Forbidden files
- Input context
- Expected output
- Required tests
- Safety notes
- Report format

Worker task template:

```markdown
# Mizuchi RepoLens Worker Task

## Worker
Worker X: <role>

## Goal
<goal>

## Allowed files
- <path>
- <path>

## Forbidden files
- mizuchi/contracts/models.py unless Manager explicitly allows it
- docs/shared_contracts.md unless Manager explicitly allows it
- CommandCenter / Task / Campaign / Codex / patch / Sheets / runtime loop files

## Context
Mizuchi RepoLens is standalone/read-only.
Do not introduce coupling to Kuchinawa runtime assumptions.
Do not write to the target repository.
Do not use shell=True.
Do not add destructive git commands.

## Task
1. ...
2. ...
3. ...

## Expected output
- changed files
- implementation summary
- tests run
- known limitations
- shared contract change requests, if any

## Stop conditions
Stop and report if:
- shared contract changes are needed
- assigned scope is insufficient
- unsafe dependency is required
- test failure cannot be resolved locally
```

## 7. Merge Gates

Worker output must pass these gates before integration.

### 7.1 Gate 1: Scope Check

Check:

- Worker changed only allowed files.
- Worker did not enter another worker's scope.
- Worker did not change shared contracts without approval.
- Worker did not make unnecessary large docs changes.

Result: `PASS` / `FIX_REQUIRED` / `REJECT`

### 7.2 Gate 2: Boundary Check

Check:

- no CommandCenter dependency
- no Task/Campaign dependency
- no Codex execution dependency
- no patch dependency
- no Sheets dependency
- no runtime loop dependency
- no Kuchinawa `PROJECT_ROOT` assumption
- no existing Kuchinawa artifacts as required inputs

Result: `PASS` / `FIX_REQUIRED` / `REJECT`

### 7.3 Gate 3: Read-only Safety Check

Check:

- no writes to target repository
- cache writes go to Mizuchi cache root
- no destructive Git verbs
- no `shell=True`
- subprocess Git goes through a read-only wrapper
- path traversal is blocked
- project root escape is blocked

Result: `PASS` / `FIX_REQUIRED` / `REJECT`

### 7.4 Gate 4: Contract Check

Check:

- `ApiResponse` / `ApiError` shape is preserved.
- `GraphData` / `Edge` / `LayoutCache` / `RenderIndex` shape is preserved.
- `GitCommitSummary` / `GitCommitDetail` / `DiffResult` shape is preserved.
- Shared contract changes, if any, are Manager-approved.

Result: `PASS` / `FIX_REQUIRED` / `REJECT`

### 7.5 Gate 5: Test Check

Required:

```bash
python3 -m compileall mizuchi tests
python3 -m unittest discover -s tests
```

Recommended:

- forbidden pattern scan
- `shell=True` scan
- destructive Git verb scan
- API smoke test
- static UI availability check

Result: `PASS` / `FIX_REQUIRED` / `ACCEPT_WITH_LIMITATION` / `REJECT`

## 8. Merge Order

Default integration order:

1. Shared contract / docs updates by Manager.
2. Worker A backend/API/cache changes.
3. Worker D Git API changes.
4. Worker B project/FileInsight adapter changes.
5. Worker C frontend changes.
6. Manager integration fixes.
7. Tests.
8. Safety scan.
9. Final report.

Reasoning:

- API/cache first makes frontend integration easier.
- Git API can be referenced by frontend and project views.
- FileInsight affects graph/detail payloads.
- Frontend last reduces conflicts.

Wave-specific exceptions are allowed, but the Manager must report why.

## 9. Conflict Resolution

Conflict types:

- same-file edit conflicts
- shared contract conflicts
- API shape mismatches
- cache path mismatches
- node id format mismatches
- graph edge id format mismatches
- frontend/backend response mismatches

Decision priority:

1. shared contracts
2. read-only safety
3. standalone independence
4. API compatibility
5. worker implementation convenience

Manager records:

- Conflict
- Files
- Workers involved
- Decision
- Reason
- Follow-up

## 10. Kuchinawa Asset Reuse

Allowed to inspect/copy/adapt:

- FileInsight evidence collection logic
- summary generation logic
- role inference logic
- Dashboard layout/components
- FileOverview/FileGraph-related UI components
- Evidence/Summary/Issue display components
- Git timeline/diff display patterns
- shared styling/theme utilities

Direct-import forbidden:

- CommandCenter
- Task/Campaign
- planner/decomposition pipeline
- Codex execution
- patch generation/application
- Sheets control plane
- validator/runtime loop
- Kuchinawa `PROJECT_ROOT` assumption
- existing Kuchinawa artifacts as required inputs

Reuse priority:

1. copy/adapt standalone-safe functions
2. build adapter boundaries
3. keep only compatible data shapes
4. avoid direct imports

Reuse reports must include:

- Source
- Destination
- Method
- Direct import
- Removed coupling
- Remaining risk

## 11. API Merge Specification

API additions/changes must:

- live under `/api/...`
- preserve `ApiResponse` / `ApiError`
- define behavior when no project is open
- validate path parameters
- avoid leaking raw exceptions
- preserve read-only boundaries

Recommended API names:

```text
GET  /api/app/status
POST /api/app/shutdown
POST /api/project/open
POST /api/project/rescan
GET  /api/project/current
GET  /api/files/tree
GET  /api/files/detail?path=...
GET  /api/graph/data
GET  /api/graph/layouts
GET  /api/graph/render-index
GET  /api/graph/edge-routes
GET  /api/git/timeline?path=...
GET  /api/git/commit?hash=...
GET  /api/git/diff?hash=...&path=...
GET  /api/settings
POST /api/settings
```

Short legacy aliases may remain for compatibility, but official paths should follow the list above.

## 12. Cache / Artifact Merge Specification

Default cache root:

`~/.cache/mizuchi-repolens/<project_hash>/`

Future macOS option:

`~/Library/Caches/mizuchi-repolens/<project_hash>/`

Cache root selection is Manager-owned.

Target artifact layout:

```text
project_manifest.json
settings.json
file_insight/
  evidence/
  summaries/
  issues/
graph/
  graph_data.json
  layout_cache.json
  edge_routes.json
  render_index.json
  manifest.json
git/
  timeline_index.json
  cochange_index.json
```

Forbidden:

- writing under the target repository
- creating `.mizuchi` or `.fileoverview` under the target repository without approval
- making generated cache a Git-tracked artifact

## 13. Frontend Merge Specification

Wave 2-3 priorities:

- minimal frontend shell
- JSON fallback/debug display
- File Tree
- Detail Pane
- Git Timeline
- Diff View
- placeholder/initial Graph View

Not yet:

- full D3 graph animation
- Trace Motion
- precise port routing UI
- GameFlow Probe UI
- CommandCenter integration UI

Dashboard reuse checks:

- no CommandCenter dependency
- no Task/Campaign dependency
- no Sheets dependency
- no runtime loop dependency
- API shape matches Mizuchi
- works in standalone static shell

## 14. Git Merge Specification

Allowed Git verbs:

- `log`
- `show`
- `diff`

Forbidden Git verbs:

- `checkout`
- `reset`
- `revert`
- `commit`
- `clean`
- `add`
- `apply`
- `merge`
- `rebase`
- branch write operations
- tag write operations

Implementation constraints:

- no `shell=True`
- `subprocess.run` uses list args
- timeout required
- commit hash validation required
- path validation required
- binary diff safety
- large diff truncation

## 15. Test Specification

Required at each wave end:

```bash
python3 -m compileall mizuchi tests
python3 -m unittest discover -s tests
```

Recommended:

- API smoke test
- static UI availability test
- Git forbidden verb test
- path traversal test
- target repository write absence test
- cache artifact write/read test

If tests fail, the Manager records:

- Command
- Failure
- Cause
- Fix
- Remaining risk

## 16. Worker Report Format

```markdown
## Worker Report

Worker:
Goal:
Changed files:
Created files:
Deleted files:
Implementation summary:
- ...
Shared contract changes:
- None / Requested
Boundary checks:
- CommandCenter dependency: none / found
- Task/Campaign dependency: none / found
- Codex execution dependency: none / found
- Patch dependency: none / found
- Sheets dependency: none / found
- target repository writes: none / found
- shell=True: none / found
- destructive git command: none / found
Tests:
- command:
- result:
Known limitations:
- ...
Needs Manager decision:
- ...
```

## 17. Manager Final Report Format

```markdown
# Mizuchi RepoLens Wave N 作業報告

## 1. Summary
...
## 2. 作業場所
...
## 3. Manager実施内容
...
## 4. Worker割当と成果
...
## 5. 作成・更新ファイル一覧
...
## 6. 実装済みAPI
...
## 7. Cache / Artifact
...
## 8. UI状態
...
## 9. Kuchinawa資産流用状況
...
## 10. 安全境界確認
...
## 11. テスト結果
...
## 12. 既知の制限
...
## 13. 次にやるとよいこと
...
## 14. Manager判断メモ
...
## 15. 最終ステータス
DONE / PARTIAL / BLOCKED / FAILED
## 16. 次回Managerへの申し送り
...
```

## 18. Wave 3 Merge Direction

Immediate Wave 3 priorities:

1. Create `README.md`.
2. Clarify repository management status.
3. Run browser smoke testing.
4. Add a minimal interactive graph viewer.
5. Connect and normalize Git co-change behavior.

Still out of scope:

- full D3 animation
- Trace Motion
- precise port routing
- GameFlow Probe
- LLM-dependent FileInsight
- CommandCenter integration

Recommended Wave 3 workers:

- Worker A: README / docs / browser smoke procedure
- Worker B: frontend interactive graph initial view
- Worker C: graph API/cache/co-change integration
- Worker D: smoke tests / safety tests / static availability

## 19. Wave 3 Manager Instruction

```markdown
# Mizuchi RepoLens Wave 3 Manager Instruction

You are the Codex Manager Session for Mizuchi RepoLens.
Wave 2 is accepted as DONE.
Proceed to Wave 3 with the goal of making Mizuchi RepoLens evaluable by a human tester.

The default operating model remains:

- Manager Session handles TODO management, shared contracts, worker assignments, integration review, safety checks, and final reporting.
- Up to 4 worker sessions may be used.
- Workers must only touch files explicitly assigned by Manager.
- Shared contracts are Manager-owned.

Primary goals:

1. Create README.md with setup, launch, cache location, safety boundary, API overview, and test commands.
2. Clarify repository management status:
   - mizuchi-repolens is currently untracked from the parent repo.
   - Decide or recommend whether to initialize it as an independent repo or include it in the parent repo.
3. Add browser smoke test procedure and, if feasible, lightweight automated smoke tests for server/API/static UI availability.
4. Replace or augment Graph JSON view with a minimal interactive graph viewer:
   - render file/folder nodes
   - render basic edges
   - support selected node highlight
   - preserve JSON fallback/debug panel
   - no full D3 animation yet
   - no Trace Motion yet
   - no precise 16/24 port routing UI yet
5. Connect Git co-change helper to graph/cache/API only if it can be done without shared contract churn.
6. Preserve standalone/read-only behavior.

Do not implement:

- CommandCenter / Task / Campaign integration
- Codex execution
- patch generation/application
- Sheets integration
- Trace Motion
- precise 16/24 port routing UI
- GameFlow Probe
- LLM-dependent FileInsight

Before assigning workers:

1. Inspect current repository state.
2. Update docs/manager_todo.md for Wave 3.
3. Update docs/worker_assignments.md for Wave 3.
4. Decide whether shared contracts need changes.
5. If shared contracts need changes, Manager must make or approve them before worker implementation.

Suggested workers:

- Worker A: README / docs / browser smoke procedure
- Worker B: minimal interactive graph viewer
- Worker C: graph API/cache/co-change integration
- Worker D: smoke tests / safety tests / static availability

Required checks before final report:

- python3 -m compileall mizuchi tests
- python3 -m unittest discover -s tests
- shell=True scan
- destructive git verb scan
- CommandCenter/Task/Campaign/Codex/patch/Sheets dependency scan
- target repository write boundary confirmation

Return final report using the Mizuchi RepoLens Manager final report format.
```

## 20. Final Rule Summary

- Manager decides.
- Workers implement only limited assigned scope.
- Shared contracts must not be changed without approval.
- Safety boundaries must not regress.
- Kuchinawa assets may be adapted, but tight coupling is forbidden.
- Target repositories are read-only.
- Worker output must pass merge gates before integration.
- Final reporting follows the Manager report format.
