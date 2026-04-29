# Mizuchi RepoLens Manager TODO

Status: Wave 5 manager setup, 2026-04-29

## Operating Specifications

- [x] Add reusable Manager/Worker merge specification: `docs/manager_worker_merge_spec.md`.
- [x] Use `docs/manager_worker_merge_spec.md` as the default merge gate, worker report, and final report reference for Wave 3 and later.

## Phase 0: Design Freeze

- [x] Read standalone specification.
- [x] Read parallel worker plan and prompt templates.
- [x] Establish shared contract file ownership.
- [x] Create initial shared data models.
- [x] Create initial worker responsibility table.
- [x] Inspect Kuchinawa FileInsight/FileOverview assets and identify safe copy/adapt candidates.
- [x] Review worker outputs before integration.

## Phase 1: Standalone Runtime

- [x] Runtime/server skeleton bound only to 127.0.0.1.
- [x] App status, current project, open project, and shutdown API skeletons.
- [x] Cache path resolver using Mizuchi cache namespace outside target repository.
- [x] Path safety helpers.

## Phase 2: Quick Scan

- [x] Project root validation.
- [x] File inventory and folder policy.
- [x] Quick scan result contract usage.
- [x] Cache artifact read/write interfaces.

## Phase 3: FileInsight Adapter

- [x] Locate reusable Kuchinawa evidence/summary/role logic.
- [x] Extract deterministic summary-lite/evidence/role placeholders behind Mizuchi adapter boundaries.
- [x] Preserve compatibility with useful Kuchinawa data shapes without runtime coupling.

## Phase 4: Graph Data

- [x] Graph builder consuming project inventory and Git co-change data.
- [x] Layout cache, edge routes, and render index stubs.
- [x] Port count and edge semantic helpers.

## Phase 5: Git Timeline / Diff

- [x] Read-only git command wrapper.
- [x] Timeline extraction.
- [x] Commit detail and diff extraction with truncation.
- [x] Co-change index builder.

## Phase 6: UI Shell

- [x] Add thin Mizuchi-owned frontend shell.
- [x] Keep UI data-driven and tolerant of empty backend data.
- [x] Avoid CommandCenter, Task/Campaign, Codex, Sheets, patch, and runtime-loop assumptions.

## Safety Checklist

- [x] No CommandCenter dependency.
- [x] No Task/Campaign dependency.
- [x] No Codex execution.
- [x] No patch generation/application.
- [x] No Sheets integration.
- [x] No target repository writes.
- [x] No Git-changing operations.
- [x] No Kuchinawa PROJECT_ROOT assumptions.
- [x] Cache under Mizuchi cache namespace outside target repository.
- [x] Server binds to 127.0.0.1 only.
- [x] subprocess calls use argument arrays and no `shell=True`.

## Wave 2: API / Cache / Minimal UI Vertical Slice

Manager status:

- [x] Confirm current repository state.
- [x] Confirm shared contracts are sufficient for Wave 2.
- [x] Keep `mizuchi/contracts/models.py` Manager-owned and unchanged for worker start.
- [x] Prepare Wave 2 worker assignments.
- [x] Review Worker A API/cache integration.
- [x] Review Worker B Project/FileInsight enrichment.
- [x] Review Worker C minimal frontend shell.
- [x] Review Worker D Git API integration.
- [x] Integrate worker outputs and resolve route/data-shape mismatches.
- [x] Run compile, unittest, and safety scans.
- [x] Sync reviewed output to the formal working directory.

Wave 2 targets:

- [x] Persist Quick Scan artifacts under Mizuchi cache.
- [x] Add file tree and file detail APIs.
- [x] Add graph data, layout cache, render index, and edge route APIs.
- [x] Add Git timeline, commit detail, and diff APIs.
- [x] Add minimal frontend shell with Open, Rescan, Shutdown, File Tree, Graph/Data, Detail, Timeline, and Diff sections.
- [x] Keep frontend tolerant of empty or missing backend data.
- [x] Preserve read-only behavior toward opened repositories.
- [x] Keep cache outside opened repositories.

Deferred beyond Wave 2:

- [ ] D3 or full graph animation.
- [ ] Trace Motion.
- [ ] Precise 16/24 port UI drawing.
- [ ] GameFlow Probe body.
- [ ] Full FileInsight LLM-dependent processing.
- [ ] CommandCenter bridge or Task/Campaign creation.

## Wave 3: Human Tester Readiness

Baseline:

- [x] Wave 2 accepted as DONE.
- [x] Baseline commit recorded: `9e2ee89 Add Mizuchi RepoLens project`.
- [x] Confirm current repository state before Wave 3 work.
- [x] Keep shared contracts Manager-owned.
- [x] Decide shared contract changes are not required for initial Wave 3 work.

Manager workflow:

- [x] Update Wave 3 TODO.
- [x] Update Wave 3 worker assignments.
- [x] Assign Worker A: README and browser smoke documentation.
- [x] Assign Worker B: minimal interactive graph viewer.
- [x] Assign Worker C: Git co-change integration investigation.
- [x] Assign Worker D: readiness and smoke-oriented tests.
- [x] Review Worker A output through merge gates.
- [x] Review Worker B output through merge gates.
- [x] Review Worker C output through merge gates.
- [x] Review Worker D output through merge gates.
- [x] Integrate accepted outputs.
- [x] Run required tests and safety scans.
- [x] Produce Wave 3 final report.

Wave 3 targets:

- [x] Add `README.md` with purpose, setup, launch, open-project flow, cache location, safety boundary, API overview, tests, and known limitations.
- [x] Add browser smoke test documentation.
- [x] Add minimal interactive graph viewer for file/folder nodes and simple edges.
- [x] Preserve graph JSON fallback/debug panel.
- [x] Support selected node highlight/details.
- [x] Investigate Git co-change graph/cache/API integration without shared contract churn.
- [x] Add lightweight Wave 3 readiness tests where practical.
- [x] Preserve standalone/read-only behavior.

Deferred beyond Wave 3 unless explicitly re-scoped:

- [ ] Full D3 graph animation.
- [ ] Trace Motion.
- [ ] Precise 16/24 port routing UI.
- [ ] GameFlow Probe.
- [ ] LLM-dependent FileInsight.
- [ ] CommandCenter, Task/Campaign, Codex, patch, Sheets, or runtime-loop integration.
- [ ] Git co-change graph/cache/API connection with path-to-`FileNode.id` normalization and bounded commit depth.

## Wave 4: Comfortable Human Testing

Baseline:

- [x] Wave 3 accepted as DONE.
- [x] Preserve Wave 3 uncommitted work as the Wave 4 baseline.
- [x] Keep shared contracts Manager-owned.
- [x] Decide shared contract changes are not required for Wave 4 UI improvements.

Manager workflow:

- [x] Update Wave 4 TODO.
- [x] Assign Worker A: browser smoke docs/results.
- [x] Review Worker A output through merge gates.
- [x] Improve File Tree from JSON-only to clickable tree UI.
- [x] Improve Git Timeline from JSON-only to readable list UI.
- [x] Improve Diff from JSON-only to readable unified diff panel.
- [x] Add low-risk graph zoom/pan controls.
- [x] Preserve JSON debug fallback panels.
- [x] Run required tests and safety scans.
- [x] Produce Wave 4 final report.

Wave 4 targets:

- [x] Document manual browser smoke test results.
- [x] Render File Tree as a clickable tree while preserving JSON debug.
- [x] Load File Detail from tree selection.
- [x] Render Git Timeline as a readable list while preserving JSON debug.
- [x] Load Diff from timeline selection.
- [x] Render Diff as readable unified diff text while preserving JSON debug.
- [x] Add basic graph zoom/pan without full animation or precise port routing.
- [x] Preserve standalone/read-only behavior.

Deferred beyond Wave 4:

- [ ] Trace Motion.
- [ ] Precise 16/24 port routing UI.
- [ ] GameFlow Probe.
- [ ] LLM-dependent FileInsight.
- [ ] CommandCenter, Task/Campaign, Codex, patch, Sheets, or runtime-loop integration.

## Wave 5: Human Evaluation Usability

Baseline:

- [x] Wave 4 accepted as DONE.
- [x] Confirm current repository state before Wave 5 work.
- [x] Confirm clickable File Tree, readable Git Timeline, readable Diff panel, SVG graph viewer, node selection, zoom/pan/reset controls, JSON debug fallback, and browser smoke docs are present.
- [x] Keep shared contracts Manager-owned.
- [x] Decide shared contract changes are not required for Wave 5 usability work.

Manager workflow:

- [x] Update Wave 5 TODO.
- [x] Update Wave 5 worker assignments.
- [x] Assign Worker A: README / tester guide / smoke docs.
- [x] Assign Worker B: File Tree search/filter.
- [x] Assign Worker C: Diff hunk navigation / timeline polish.
- [x] Assign Worker D: Graph mouse interactions / frontend tests.
- [x] Review Worker A output through merge gates.
- [x] Review Worker B output through merge gates.
- [x] Review Worker C output through merge gates.
- [x] Review Worker D output through merge gates.
- [x] Integrate accepted outputs.
- [x] Run required Wave 5 checks.
- [x] Sync reviewed output to the formal working directory.
- [ ] Produce Wave 5 final report.

Wave 5 targets:

- [x] Improve README with shortest launch path, project opening, File Tree/Graph/Timeline/Diff usage, safety/read-only boundary, known limitations, and shutdown.
- [x] Add low-risk File Tree search/filter while preserving click behavior and JSON debug fallback.
- [x] Improve Diff hunk visibility/navigation and make truncated state obvious while preserving raw debug.
- [x] Improve Graph mouse wheel zoom and drag pan while preserving controls and node selection.
- [x] Improve Git Timeline selected commit/diff state visibility while preserving JSON debug.
- [x] Preserve standalone/read-only behavior.

Deferred beyond Wave 5:

- [ ] Trace Motion.
- [ ] Precise 16/24 port routing UI.
- [ ] GameFlow Probe.
- [ ] LLM-dependent FileInsight.
- [ ] CommandCenter / Task / Campaign integration.
- [ ] Codex execution.
- [ ] patch generation/application.
- [ ] Sheets integration.
