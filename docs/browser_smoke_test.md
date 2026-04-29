# Browser Smoke Test

Use this procedure to verify that Mizuchi RepoLens is human-evaluable from a browser while preserving the read-only safety boundary.

## Preconditions

- Python 3.11 or newer is available.
- Run commands from the Mizuchi RepoLens project root.
- Choose a local Git repository to inspect. The repository should have at least one tracked file and one commit so Git Timeline and Diff can be checked.

## 1. Shortest Launch

From the Mizuchi RepoLens project root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m mizuchi --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

The UI is served from localhost only.

Expected:

- The page title/header shows `Mizuchi RepoLens`.
- `Project current status` shows `Online`.
- No project is open yet unless `--open-project` was used.

Optional one-command project open after setup:

```bash
python -m mizuchi --port 8765 --open-project /absolute/path/to/repo
```

## 2. Open Project

1. Enter the absolute path to the test repository in `Project path`.
2. Click `Open`.
3. Confirm the status panel updates with the selected project path.
4. Confirm the cache path is outside the selected repository.
5. Confirm Git status says `Git repository` for a Git repo.
6. Click `Rescan`.

Expected:

- The notice reports `Project opened.` after opening.
- The notice reports `Rescan complete.` after scanning.
- The target repository has no modified files caused by RepoLens.

Read-only safety check:

- Before and after the smoke test, use your normal Git status tool in the opened repository.
- Expected result: RepoLens does not create, modify, delete, checkout, reset, or otherwise change files in the opened repository.

## 3. Verify File Tree

1. Find the `File Tree` panel.
2. Click `Refresh` if needed.
3. Confirm the clickable tree appears above the JSON debug payload.
4. Expand or collapse at least one folder.
5. Click a known file.

Expected:

- The payload includes a root folder with the project display name.
- Known files from the selected repository appear as project-relative paths.
- Clicking a file copies its path into File Detail and loads its detail payload.
- Folders and files are represented without absolute target-repository paths in child entries.
- The JSON debug payload remains available below the tree.

## 4. Verify File Detail

1. In `File Detail`, enter a known project-relative file path, for example `README.md`.
2. Click `Load`.
3. Inspect the JSON payload.

Expected:

- `path` matches the project-relative path entered.
- `content_text` contains the file's text.
- `size_bytes`, `encoding`, and `truncated` are present.
- `insight` is either a fallback insight object or `null`.

Safety check:

- Enter `../README.md` and click `Load`.
- Expected result is an error notice or rejected response, not a file outside the project.

## 5. Verify Graph View

1. Find the `Graph` panel after `Rescan`.
2. Confirm the graph canvas renders file/folder nodes when graph data is available.
3. Use zoom, pan, and reset controls.
4. Select a node in the graph canvas.
5. Inspect the `Selected node` detail area.
6. Inspect the JSON debug payload below the canvas.

Expected:

- The SVG graph canvas is visible.
- File and folder nodes render without requiring D3 or external assets.
- Selecting a node highlights it and shows node metadata.
- Zoom, pan, and reset controls do not break node selection.
- The payload includes `nodes`, `edges`, `project_hash`, and `metadata`.
- Known files appear as graph file nodes.
- The JSON debug panel remains available for raw API inspection.

## 6. Verify Git Timeline

1. Find the `Git Timeline` panel.
2. Click `Refresh`.
3. Confirm a readable timeline list appears above the JSON debug payload.
4. Click a commit row.

Expected:

- A Git repository returns recent commit entries.
- Each entry includes commit identity fields such as hash, subject/message, author, and date fields according to the API payload.
- Clicking a commit fills the Diff input and loads the Diff panel.
- The JSON debug payload remains available below the timeline list.
- A non-Git folder may return a Git request error.

Record one commit hash for the Diff check.

## 7. Verify Diff View

1. Paste a commit hash from Git Timeline into the `Diff` input.
2. Click `Load`.
3. Confirm the readable unified diff panel appears above the JSON debug payload.
4. Inspect the JSON debug payload.

Expected:

- The payload describes the requested commit diff.
- Changed files and diff text or truncated diff data are present.
- Added, removed, hunk, and header lines are visually distinguishable when present.
- The JSON debug payload remains available below the readable diff.
- The operation does not checkout, reset, or otherwise change the repository.

## 8. Shutdown

Click `Shutdown` in the page header, or press `Ctrl-C` in the terminal running the server.

Expected:

- The page notice reports `Server shutdown requested.` when using the button.
- The terminal process exits cleanly.
- Refreshing the page after shutdown no longer reaches the server.

## Known Limitations To Keep In Mind

- File and graph data come from a lightweight Quick Scan.
- The graph is a simple SVG overview, not a full dependency explorer.
- Non-Git folders can be opened, but Git Timeline and Diff require a Git repository.
- Large files and large diffs may be truncated.
- JSON debug panels are intentionally preserved to help testers inspect raw payloads.
