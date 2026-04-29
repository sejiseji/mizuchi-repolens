# Mizuchi RepoLens Worker Assignments

Date: 2026-04-29

All workers may inspect Kuchinawa resources, but each worker task must only touch the files explicitly assigned by the Manager. Do not modify CommandCenter, Task/Campaign, Codex execution, Sheets, patch, or runtime loop code. If shared contracts must change, stop and report it to the Manager instead of changing them locally.

For Wave 3 and later, use `docs/manager_worker_merge_spec.md` as the default source for worker assignment fields, merge gates, safety checks, and worker report format.

## Shared Forbidden Scope

- CommandCenter
- Task/Campaign creation or execution
- planner/decomposition pipeline
- Codex execution
- patch generation or patch apply
- Sheets control plane
- validator/runtime loop
- target repository writes
- Git-changing operations such as checkout/reset/revert/commit/add/clean/apply
- Kuchinawa `PROJECT_ROOT` assumptions
- existing Kuchinawa artifacts as required inputs

## Worker A: Runtime / API / Security / Storage

Objective: implement a minimal standalone runtime and API shell that can later host the RepoLens UI and scan pipeline.

Allowed files/directories:

- `mizuchi/__main__.py`
- `mizuchi/runtime/`
- `mizuchi/api/`
- `mizuchi/security/`
- `mizuchi/storage/`
- `tests/test_runtime*.py`
- `tests/test_security*.py`
- `tests/test_storage*.py`

Expected output:

- CLI entrypoint skeleton for `python -m mizuchi`.
- Local server skeleton bound to `127.0.0.1` only, or a clearly documented placeholder if no framework is introduced.
- Status, shutdown, open project, and current project API handlers.
- Cache path resolver under the Mizuchi cache namespace outside the target repository.
- Path safety helpers for project-relative access.

Checks:

- Run focused tests for runtime/security/storage if added.
- Confirm no `shell=True`.
- Confirm no target repository write path.

Stop and ask Manager if:

- A new dependency or shared contract change is required.
- API response shape needs to change.
- Runtime would need to write into the opened repository.

## Worker B: Project Inventory / FileInsight Adapter

Objective: implement project scanning foundations and FileInsight adapter stubs without coupling to Kuchinawa core.

Allowed files/directories:

- `mizuchi/project/`
- `mizuchi/insight/`
- `mizuchi/analyzers/`
- `tests/test_project*.py`
- `tests/test_insight*.py`
- `tests/test_analyzers*.py`

Expected output:

- Project root validation using read-only checks.
- File inventory with default folder capture policy.
- Quick scan result builder using shared `FileNode` and `FolderNode`.
- FileInsight evidence/summary/role/issue adapter interfaces with empty or lightweight fallback implementations.
- Cache artifact interface definitions for insight outputs; actual writes must target Mizuchi cache paths only.

Checks:

- Run focused tests for inventory and folder policy if added.
- Confirm adapter has no CommandCenter, Task/Campaign, Codex, Sheets, patch, or runtime-loop imports.

Stop and ask Manager if:

- Kuchinawa reuse requires importing forbidden core modules.
- Shared FileInsight output contracts need changing.
- Scan behavior would write to the opened repository.

## Worker C: Graph Data / Layout / Edge Semantics

Objective: implement graph data and layout helper skeletons on top of Manager-owned contracts.

Allowed files/directories:

- `mizuchi/graph/`
- `tests/test_graph*.py`

Expected output:

- Graph builder helpers for folder, dependency, co-change, and domain-placeholder views.
- Edge semantic helpers for relation tags, certainty, direction, and weight.
- Layout cache placeholder generation for all view modes.
- 16/24 port selection and edge route placeholder helpers.
- Render index builder for view mode and relation-tag lookup.

Checks:

- Run focused graph tests if added.
- Confirm graph view switching consumes cached/indexed data and does not trigger scans.

Stop and ask Manager if:

- Shared graph contracts need fields changed.
- Git subprocess calls seem necessary.
- UI-specific assumptions are needed.

## Worker D: Git Timeline / Diff / Co-change

Objective: implement a read-only git client and timeline/diff extraction skeleton.

Allowed files/directories:

- `mizuchi/git/`
- `tests/test_git*.py`

Expected output:

- Safe git client allowing only `git log`, `git show`, and `git diff`.
- Commit hash validation.
- Timeline extraction with depth limit.
- Commit detail extraction.
- Diff extraction with timeout and truncation.
- Co-change edge/index builder compatible with shared graph contracts.

Checks:

- Run focused git tests if added.
- Confirm all subprocess calls use argument arrays and no `shell=True`.
- Confirm forbidden git verbs are rejected.

Stop and ask Manager if:

- A Git-changing command appears necessary.
- Diff model fields need changing.
- Target repository writes or checkout-like behavior would be required.

---

# Wave 2 Worker Assignments

Date: 2026-04-29

Wave 2 goal: connect the backend skeleton to a minimal browser-visible UI while preserving standalone/read-only behavior. Shared contracts remain Manager-owned; workers must not edit `mizuchi/contracts/models.py` or `docs/shared_contracts.md`.

## Wave 2 Shared Stop Conditions

Stop and report to Manager if:

- A shared contract field or model appears necessary.
- An implementation would write into the opened target repository.
- A Kuchinawa import pulls in CommandCenter, Task/Campaign, Codex execution, patch, Sheets, validator, or runtime-loop behavior.
- A git-changing operation appears necessary.
- `shell=True` appears necessary.
- Work requires files outside the worker's assigned scope.

## Wave 2 Worker A: API / Cache Integration

Objective: expose Quick Scan cache artifacts and file/graph APIs through the stdlib API server.

Allowed files/directories:

- `mizuchi/api/`
- `mizuchi/storage/`
- `mizuchi/project/`
- `tests/test_api*.py`
- `tests/test_storage*.py`
- `tests/test_project*.py`

Expected APIs:

- `GET /api/files/tree`
- `GET /api/files/detail?path=...`
- `GET /api/graph/data`
- `GET /api/graph/layouts`
- `GET /api/graph/render-index`
- `GET /api/graph/edge-routes`
- `POST /api/project/rescan`

Expected output:

- Quick Scan artifact read/write helpers under Mizuchi cache.
- API handlers that return `ApiResponse` envelopes.
- Path traversal protection for file detail.
- Empty/error responses when no project is open.
- Focused unittest coverage.

## Wave 2 Worker B: Project Inventory / FileInsight Adapter Enrichment

Objective: enrich the deterministic Quick Scan and FileInsight placeholder data without direct Kuchinawa runtime imports.

Allowed files/directories:

- `mizuchi/project/`
- `mizuchi/insight/`
- `mizuchi/analyzers/`
- `docs/kuchinawa_reuse_notes.md`
- `tests/test_project*.py`
- `tests/test_insight*.py`
- `tests/test_analyzers*.py`

Expected output:

- More stable Summary-lite and Evidence placeholder shape for file detail.
- Deterministic role inference improvements for common project files.
- Inventory payload helpers that Worker A can cache.
- Notes on any Kuchinawa FileInsight logic inspected or copy/adapted.
- Focused unittest coverage.

Forbidden:

- Direct import from `runner/file_insight_engine`.
- Dependency on Kuchinawa `artifact_dir()`, policy objects, `PROJECT_ROOT`, or existing artifacts.

## Wave 2 Worker C: Minimal Frontend Shell

Objective: add a thin Mizuchi-owned frontend shell and static serving.

Allowed files/directories:

- `mizuchi/static/`
- `mizuchi/api/`
- `tests/test_frontend*.py`
- `tests/test_runtime*.py`

Expected output:

- Browser-visible shell with Open, Rescan, Shutdown controls.
- Project current status section.
- File Tree section.
- Graph placeholder or graph JSON view.
- File Detail section.
- Git Timeline and Diff sections.
- Static serving from the local API server.
- No CommandCenter, Task/Campaign, Sheets, patch, or Codex UI concepts.

## Wave 2 Worker D: Git Timeline / Commit Detail / Diff API Integration

Objective: expose read-only Git timeline, commit detail, and diff data through APIs.

Allowed files/directories:

- `mizuchi/git/`
- `mizuchi/api/`
- `tests/test_git*.py`
- `tests/test_api_git*.py`

Expected APIs:

- `GET /api/git/timeline?path=...`
- `GET /api/git/commit?hash=...`
- `GET /api/git/diff?hash=...&path=...`

Expected output:

- API handlers wired to the read-only git client.
- Diff truncation surfaced in response payloads.
- Commit hash validation preserved.
- Optional path filter validation for timeline and diff.
- Focused unittest coverage.

Git safety:

- Allowed verbs: `log`, `show`, `diff`.
- Forbidden verbs: `checkout`, `reset`, `revert`, `commit`, `clean`, `add`, `apply`.
- `shell=True` forbidden.

---

# Wave 3 Worker Assignments

Date: 2026-04-29

Wave 3 goal: make Mizuchi RepoLens evaluable by a human tester. Wave 2 is accepted as DONE at baseline commit `9e2ee89 Add Mizuchi RepoLens project`.

Shared contracts remain Manager-owned. Workers must not edit `mizuchi/contracts/models.py` or `docs/shared_contracts.md` unless the Manager explicitly approves it.

## Wave 3 Shared Stop Conditions

Stop and report to Manager if:

- A shared contract field or model change appears necessary.
- An implementation would write into the opened target repository.
- A Kuchinawa import would pull in CommandCenter, Task/Campaign, Codex execution, patch, Sheets, validator, or runtime-loop behavior.
- A git-changing operation appears necessary.
- `shell=True` appears necessary.
- Work requires files outside the assigned scope.

## Wave 3 Worker A: README / Browser Smoke Documentation

Goal: add human-tester documentation for setup, launch, manual browser checks, and known limits.

Allowed files:

- `README.md`
- `docs/browser_smoke_test.md`

Expected output:

- README covering purpose, setup, launch command, open project flow, cache location, read-only safety boundary, API overview, test commands, and known limitations.
- Browser smoke test guide covering launch, open repo, File Tree, File Detail, Graph view, Git Timeline, Diff view, and shutdown.

Required checks:

- Documentation review.
- No implementation or shared contract changes.

## Wave 3 Worker B: Minimal Interactive Graph Viewer

Goal: augment the JSON-only graph section with a minimal static, dependency-free graph viewer.

Allowed files:

- `mizuchi/static/index.html`
- `mizuchi/static/app.js`
- `mizuchi/static/styles.css`
- `tests/test_frontend_static.py`

Expected output:

- Render file/folder nodes from `/api/graph/data`.
- Render simple edges.
- Support selected node highlight and selected node details.
- Preserve JSON fallback/debug panel.
- Remain tolerant of empty or missing graph data.
- Avoid D3, Trace Motion, and precise 16/24 port routing UI.

Required checks:

- Focused frontend static tests.
- No backend or shared contract changes.

## Wave 3 Worker C: Git Co-change Integration Investigation

Goal: determine whether Git co-change graph/cache/API integration can be safely connected without shared contract churn.

Allowed files:

- `docs/wave3_cochange_notes.md`

Expected output:

- Findings on current `mizuchi/git/cochange.py` and graph/cache/API shapes.
- Decision recommendation: connect in Wave 3 or defer.
- Risks, required follow-up, and any shared contract change request.

Required checks:

- Documentation review.
- No implementation or shared contract changes.

## Wave 3 Worker D: Smoke Tests / Safety Tests / Static Availability

Goal: add lightweight readiness tests that support Wave 3 human evaluation.

Allowed files:

- `tests/test_wave3_readiness.py`

Expected output:

- Stdlib-only tests for documentation/static readiness where practical.
- Tests remain deterministic and avoid network except local server patterns already used by the suite.

Required checks:

- `python3 -m unittest tests.test_wave3_readiness`
- No implementation or shared contract changes.

---

# Wave 4 Worker Assignments

Date: 2026-04-29

Wave 4 goal: improve Mizuchi RepoLens from technically evaluable to comfortably human-testable.

Shared contracts remain Manager-owned. Workers must not edit `mizuchi/contracts/models.py` or `docs/shared_contracts.md` unless the Manager explicitly approves it.

## Wave 4 Shared Stop Conditions

Stop and report to Manager if:

- A shared contract field or model change appears necessary.
- Any implementation would write into the opened target repository.
- A Kuchinawa import would pull in CommandCenter, Task/Campaign, Codex execution, patch, Sheets, validator, or runtime-loop behavior.
- A git-changing operation appears necessary.
- `shell=True` appears necessary.
- Work requires files outside the assigned scope.

## Wave 4 Worker A: Browser Smoke Test / Docs

Goal: document Wave 4 smoke readiness and keep human-tester docs aligned with the UI.

Allowed files:

- `README.md`
- `docs/browser_smoke_test.md`
- `docs/wave4_smoke_results.md`

Expected output:

- Browser smoke documentation updated for clickable File Tree, readable Git Timeline, readable Diff panel, and Graph JSON debug.
- Smoke results or a documented manual smoke checklist when full browser interaction is not possible.

Required checks:

- Documentation review.
- No implementation, tests, or shared contract changes.

## Wave 4 Manager-Owned UI Integration

Goal: avoid same-file worker conflicts by integrating the static UI improvements in the Manager session.

Allowed files:

- `mizuchi/static/index.html`
- `mizuchi/static/app.js`
- `mizuchi/static/styles.css`
- `tests/test_frontend_static.py`
- `tests/test_wave3_readiness.py`

Expected output:

- Clickable File Tree with File Detail loading.
- Readable Git Timeline list with Diff loading.
- Readable unified diff panel.
- Basic graph zoom/pan controls.
- JSON fallback/debug panels preserved.
- No backend or shared contract changes.

---

# Wave 5 Worker Assignments

Date: 2026-04-29

Wave 5 goal: prepare Mizuchi RepoLens for human evaluation by improving usability and reducing friction in the current UI.

Shared contracts remain Manager-owned. Workers must not edit `mizuchi/contracts/models.py` or `docs/shared_contracts.md`.

## Wave 5 Shared Stop Conditions

Stop and report to Manager if:

- A shared contract field or model change appears necessary.
- Any implementation would write into the opened target repository.
- A Kuchinawa import would pull in CommandCenter, Task/Campaign, Codex execution, patch, Sheets, validator, or runtime-loop behavior.
- A git-changing operation appears necessary.
- `shell=True` appears necessary.
- Work requires files outside the assigned scope.

Forbidden for Wave 5:

- Trace Motion
- precise 16/24 port routing UI
- GameFlow Probe
- LLM-dependent FileInsight
- CommandCenter / Task / Campaign integration
- Codex execution
- patch generation/application
- Sheets integration
- destructive git operations
- target repository writes

## Wave 5 Worker A: README / Tester Guide / Smoke Docs

Goal: make the project easy for human testers to launch and evaluate.

Allowed files:

- `README.md`
- `docs/browser_smoke_test.md`
- `docs/wave4_smoke_results.md`

Expected output:

- shortest launch path
- how to open a project
- how to use File Tree / Graph / Timeline / Diff
- what is safe/read-only
- known limitations
- how to stop the server

Required checks:

- Documentation review.
- No implementation, test, or shared contract changes.

## Wave 5 Worker B: File Tree Search / Filter

Goal: add a low-risk File Tree search/filter without breaking tree clicks.

Allowed files:

- `mizuchi/static/index.html`
- `mizuchi/static/app.js`
- `mizuchi/static/styles.css`
- `tests/test_frontend_static.py`
- `tests/test_wave3_readiness.py`

Expected output:

- File Tree search/filter control.
- Existing tree click behavior preserved.
- JSON debug fallback preserved.
- Clear empty filter state.

Required checks:

- `node --check mizuchi/static/app.js`
- Focused unittest where practical.

## Wave 5 Worker C: Diff Hunk Navigation / Timeline Polish

Goal: improve diff and timeline usability without changing backend contracts.

Allowed files:

- `mizuchi/static/index.html`
- `mizuchi/static/app.js`
- `mizuchi/static/styles.css`
- `tests/test_frontend_static.py`
- `tests/test_wave3_readiness.py`

Expected output:

- Hunk navigation or hunk headings if low-risk.
- Truncated diff state is obvious.
- Selected commit/diff state is visible.
- Raw JSON debug information preserved.

Required checks:

- `node --check mizuchi/static/app.js`
- Focused unittest where practical.

## Wave 5 Worker D: Graph Mouse Interactions / Frontend Tests

Goal: add low-risk graph mouse wheel zoom and drag pan.

Allowed files:

- `mizuchi/static/app.js`
- `mizuchi/static/styles.css`
- `tests/test_frontend_static.py`
- `tests/test_wave3_readiness.py`

Expected output:

- Mouse wheel zoom.
- Drag pan.
- Existing zoom/pan/reset controls preserved.
- Node selection preserved.
- No full animation or precise port routing UI.

Required checks:

- `node --check mizuchi/static/app.js`
- Focused unittest where practical.
