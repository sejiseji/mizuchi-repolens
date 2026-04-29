# Mizuchi RepoLens

Mizuchi RepoLens is a standalone, read-only repository insight viewer. It opens a local project directory, serves a browser UI on localhost, scans source files into cached JSON artifacts, and shows file, graph, git timeline, and diff views for human evaluation.

RepoLens is designed to inspect a project without modifying it.

## Setup

Requirements:

- Python 3.11 or newer
- Git, when testing Git Timeline or Diff views

From the project root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

The project currently uses only the Python standard library at runtime.

## Shortest Launch Path

From the Mizuchi RepoLens project root:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m mizuchi --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

This is a localhost-only browser UI.

To open a project at startup, pass an absolute path:

```bash
python -m mizuchi --port 8765 --open-project /path/to/repo
```

The server binds only to `127.0.0.1`. Stop it with `Ctrl-C` in the terminal or the UI's `Shutdown` button.

## Open A Project

1. Launch the server and open the browser UI.
2. Enter an absolute path to a local repository or folder in `Project path`.
3. Click `Open`.
4. Confirm `Project current status` shows the selected path, cache directory, and Git status.
5. Click `Rescan` to build the cached data used by File Tree, File Detail, and Graph.

Use an absolute path for the project itself. Use project-relative paths inside the file detail and optional Git path filters, for example `README.md`.

## Use The Views

### File Tree And File Detail

- Click `Refresh` in File Tree if the tree is empty after opening or rescanning.
- Expand folders to browse the project.
- Click a file to load it in File Detail.
- You can also type a project-relative path in File Detail and click `Load`.
- The JSON debug payload remains available below the readable tree/detail view.

### Graph

- Click `Rescan` first if no graph appears.
- Use the graph canvas to inspect file and folder nodes.
- Click a node to show its metadata in `Selected node`.
- Use the zoom, pan, and reset controls for basic navigation.
- Use the JSON debug payload when checking raw node and edge data.

### Git Timeline

- Open a Git repository, then click `Refresh` in Git Timeline.
- Click a commit row to select it and load the Diff view.
- A non-Git folder can still be opened, but Timeline and Diff will report Git errors.

### Diff

- Load Diff from a Timeline commit, or paste a commit hash into the Diff input and click `Load`.
- Review the readable unified diff panel first.
- Use the JSON debug payload below it to confirm truncation flags, changed files, and raw diff data.

## Cache Location

RepoLens writes its own generated artifacts outside the opened project. Cache root resolution is:

1. `MIZUCHI_CACHE_HOME`, when set
2. `$XDG_CACHE_HOME/mizuchi-repolens`, when `XDG_CACHE_HOME` is set
3. `~/.cache/mizuchi-repolens`

Each opened project gets a project-hash subdirectory. Quick Scan artifacts are written under:

```text
<cache-root>/<project-hash>/quick_scan/
```

The cache root is rejected if it would be inside the opened target repository.

## Read-Only Safety Boundary

RepoLens treats the opened project as read-only.

- File APIs read project-relative files and reject absolute paths or traversal.
- Scans read inventory and file content, then write artifacts only to the Mizuchi cache.
- Git operations are limited to read-only data extraction with `git log`, `git show`, and `git diff`.
- The server is local-only and binds to `127.0.0.1`.
- RepoLens should not create, modify, delete, checkout, reset, or otherwise change files in the opened project.

## Stop The Server

Use either option:

- Click `Shutdown` in the page header.
- Press `Ctrl-C` in the terminal running `python -m mizuchi`.

After shutdown, refreshing `http://127.0.0.1:8765/` should no longer reach the server.

## API Overview

All JSON API handlers return an `ApiResponse` envelope:

```json
{ "ok": true, "data": {} }
```

or:

```json
{ "ok": false, "error": { "code": "error_code", "message": "details" } }
```

Available endpoints:

- `GET /api/app/status` - server status and local-only flag.
- `GET /api/project/current` - currently opened project and cache path.
- `POST /api/project/open` - open a project with body `{"path": "/path/to/repo"}`.
- `POST /api/project/rescan` - run Quick Scan and refresh cached artifacts.
- `POST /api/app/shutdown` - request local server shutdown.
- `GET /api/files/tree` - cached file tree.
- `GET /api/files/detail?path=README.md` - file content and fallback insight for a project-relative path.
- `GET /api/graph/data` - cached graph nodes and edges.
- `GET /api/graph/layouts` - cached layout payloads.
- `GET /api/graph/render-index` - cached render lookup data.
- `GET /api/graph/edge-routes` - cached routed edge data.
- `GET /api/git/timeline` - read-only commit timeline, optionally filtered by `path`.
- `GET /api/git/commit?hash=<commit>` - read-only commit detail.
- `GET /api/git/diff?hash=<commit>` - read-only commit diff, optionally filtered by `path`.

## Tests

Run the compile check:

```bash
python3 -m compileall mizuchi tests
```

Run all tests:

```bash
python3 -m unittest discover -s tests
```

Run focused groups:

```bash
python -m unittest tests.test_runtime_api tests.test_frontend_static
python -m unittest tests.test_api_quick_scan tests.test_api_git
python -m unittest tests.test_git_client tests.test_git_timeline tests.test_git_cochange
python -m unittest tests.test_graph_builders tests.test_graph_layout_routing
```

For manual browser smoke coverage, follow `docs/browser_smoke_test.md`. Current Wave 4 smoke results are recorded in `docs/wave4_smoke_results.md`.

## Known Limitations

- The graph viewer is a minimal static SVG overview with simple layout, selection, zoom/pan controls, and JSON debug output.
- File Tree is clickable, with raw tree JSON kept as a debugging fallback.
- File Detail can be loaded from the tree or by manually entering a project-relative path.
- Git Timeline and Diff have readable panels, with JSON debug panels preserved.
- Diff view can be loaded from timeline selection or by manually entering a commit hash.
- Graph and file insight data depend on the lightweight Quick Scan fallback analyzer.
- Non-Git folders can be opened, but Git Timeline and Diff APIs require a Git repository.
- Large file detail responses are truncated to the first 65,536 bytes.
- Large diffs may be truncated in the readable and JSON views.
