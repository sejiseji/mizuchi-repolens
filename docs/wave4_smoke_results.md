# Wave 4 Smoke Results

Date: 2026-04-29

Scope: local smoke check for Wave 4 human-testability work.

Use this file as historical smoke evidence. For a fresh human evaluation, follow `docs/browser_smoke_test.md`.

Server:

- URL: `http://127.0.0.1:8766`
- Note: port `8765` was already in use, so the server was started on `8766`.
- Target opened for smoke: `<MIZUCHI_REPOLENS_ROOT>`

## Result Summary

| Check | Result | Notes |
|---|---|---|
| Server status | OK | `/api/app/status` returned `ok: true`. |
| Open project | OK | `/api/project/open` accepted the Mizuchi RepoLens project path. |
| Rescan | OK | `node_count=90`, `edge_count=89`. |
| File Tree API | OK | Root payload returned. |
| File Detail API | OK | `README.md` loaded successfully. |
| Graph API | OK | `nodes=90`, `edges=89`. |
| Git Timeline API | OK | 2 commits returned from the current parent Git history. |
| Diff API | OK | Diff text returned. `truncated=true` for the selected commit. |

## Browser UI Coverage

The local API smoke confirms that the data needed by the browser UI is available. The current UI includes:

- Clickable File Tree with JSON debug fallback.
- File Detail loading from selected tree files or manual path input.
- SVG Graph viewer with node selection, basic zoom/pan controls, and JSON debug fallback.
- Readable Git Timeline list with JSON debug fallback.
- Readable unified Diff panel with JSON debug fallback.
- Open, Rescan, and Shutdown controls.

## Remaining Manual Checks

These checks should still be verified by a human in the browser:

1. Expand and collapse folders in the File Tree.
2. Click a tree file and confirm File Detail updates.
3. Select graph nodes and confirm selected-node metadata updates.
4. Use graph zoom/pan controls and reset.
5. Click a Git Timeline commit and confirm Diff loads.
6. Confirm the readable Diff panel is comfortable to scan.
7. Click Shutdown and confirm the server exits.

## Human Evaluation Launch Notes

- Shortest launch path: create/activate `.venv`, install with `python -m pip install -e .`, run `python -m mizuchi --port 8765`, then open `http://127.0.0.1:8765/`.
- Open a project by entering an absolute local path in `Project path`, clicking `Open`, then clicking `Rescan`.
- Use File Tree to browse and load files, Graph to inspect the SVG overview, Git Timeline to select commits, and Diff to review the selected commit.
- Stop the server with the page `Shutdown` button or `Ctrl-C` in the server terminal.

## Safety Notes

- Smoke operations read the target project and wrote generated artifacts only to the Mizuchi cache.
- No destructive Git operation was used.
- No target repository write was required.
- Testers should confirm the opened repository's Git status remains unchanged after evaluation.
