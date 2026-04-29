"""Stdlib local HTTP server for Mizuchi RepoLens."""

from __future__ import annotations

import json
import mimetypes
import threading
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from mizuchi.analyzers import quick_scan_project, quick_scan_result_to_payload
from mizuchi.contracts.models import ApiResponse, CachePath, FileNode, FolderNode, GraphData, ProjectRoot, ViewMode
from mizuchi.git import (
    GitClient,
    GitClientError,
    GitCommandError,
    GitTimeoutError,
    get_commit_detail,
    get_commit_diff,
    get_timeline,
)
from mizuchi.graph import build_edge_routes, build_folder_view, build_layout_cache, build_render_index
from mizuchi.project.paths import ProjectPathError, safe_project_relative_path
from mizuchi.runtime.project import ProjectOpenError
from mizuchi.runtime.state import RuntimeState
from mizuchi.storage.cache import CachePathError, read_quick_scan_artifact, write_quick_scan_artifact


LOCAL_HOST = "127.0.0.1"
STATIC_ROOT = Path(__file__).resolve().parents[1] / "static"
STATIC_INDEX = "index.html"


class MizuchiHTTPServer(ThreadingHTTPServer):
    """HTTP server with Mizuchi runtime state attached."""

    def __init__(self, server_address: tuple[str, int], state: RuntimeState):
        host, _port = server_address
        if host != LOCAL_HOST:
            raise ValueError("Mizuchi server must bind to 127.0.0.1")
        self.state = state
        super().__init__(server_address, MizuchiRequestHandler)


def create_server(port: int, state: RuntimeState | None = None) -> MizuchiHTTPServer:
    return MizuchiHTTPServer((LOCAL_HOST, port), state or RuntimeState())


def _response_payload(response: ApiResponse[Any]) -> bytes:
    return json.dumps(asdict(response), default=str).encode("utf-8")


def _json_data(value: Any) -> Any:
    if hasattr(value, "as_json"):
        return value.as_json()
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    if isinstance(value, dict):
        return {str(key): _json_data(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_data(item) for item in value]
    return value


class MizuchiRequestHandler(BaseHTTPRequestHandler):
    server: MizuchiHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        query = parse_qs(parsed.query, keep_blank_values=True)

        if route in {"/", f"/{STATIC_INDEX}"}:
            self._send_static_file(STATIC_ROOT / STATIC_INDEX)
            return
        if route.startswith("/static/"):
            self._handle_static_asset(route)
            return
        if route in {"/api/app/status", "/api/status"}:
            self._send_success({"status": "ok", "local_only": True})
            return
        if route in {"/api/project/current", "/api/project"}:
            self._send_success(self.server.state.current_project_json())
            return
        if route == "/api/files/tree":
            self._handle_files_tree()
            return
        if route == "/api/files/detail":
            self._handle_file_detail(query)
            return
        if route == "/api/graph/data":
            self._handle_cached_artifact("graph_data", self._empty_graph_data)
            return
        if route == "/api/graph/layouts":
            self._handle_cached_artifact("graph_layouts", self._empty_layouts)
            return
        if route == "/api/graph/render-index":
            self._handle_cached_artifact("graph_render_index", self._empty_render_index)
            return
        if route == "/api/graph/edge-routes":
            self._handle_cached_artifact("graph_edge_routes", self._empty_edge_routes)
            return
        if route == "/api/git/timeline":
            self._handle_git_timeline(query)
            return
        if route == "/api/git/commit":
            self._handle_git_commit(query)
            return
        if route == "/api/git/diff":
            self._handle_git_diff(query)
            return
        self._send_failure(HTTPStatus.NOT_FOUND, "not_found", "unknown endpoint")

    def do_POST(self) -> None:
        route = urlparse(self.path).path
        if route == "/api/project/open":
            self._handle_open_project()
            return
        if route == "/api/project/rescan":
            self._handle_project_rescan()
            return
        if route in {"/api/app/shutdown", "/api/shutdown"}:
            self._send_success({"shutting_down": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        self._send_failure(HTTPStatus.NOT_FOUND, "not_found", "unknown endpoint")

    def _handle_open_project(self) -> None:
        try:
            payload = self._read_json()
            path = payload.get("path")
            if not isinstance(path, str) or not path:
                self._send_failure(HTTPStatus.BAD_REQUEST, "bad_request", "path is required")
                return

            project = self.server.state.open_project(path)
            self._send_success(self.server.state.current_project_json() or {"project": project.as_json()})
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_failure(HTTPStatus.BAD_REQUEST, "bad_json", "request body must be valid JSON")
        except (ProjectOpenError, CachePathError, OSError) as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "open_project_failed", str(exc))

    def _handle_project_rescan(self) -> None:
        project, cache_path = self._current_project_and_cache()
        if project is None or cache_path is None:
            return

        try:
            scan = quick_scan_project(project.path)
            quick_scan_payload = quick_scan_result_to_payload(scan)
            graph = self._graph_with_folder_edges(scan.graph)
            layouts = build_layout_cache(graph)
            render_index = build_render_index(graph)
            edge_routes = build_edge_routes(graph.edges, layouts.layouts[ViewMode.FOLDER], graph.nodes)
            files_tree = self._files_tree_from_graph(project, graph)

            artifacts = {
                "quick_scan": quick_scan_payload,
                "file_inventory": quick_scan_payload.get("inventory") or {},
                "file_insights": {"items": quick_scan_payload.get("insights") or []},
                "files_tree": files_tree,
                "graph_data": _json_data(graph),
                "graph_layouts": _json_data(layouts),
                "graph_render_index": _json_data(render_index),
                "graph_edge_routes": _json_data(edge_routes),
            }
            for artifact_name, payload in artifacts.items():
                write_quick_scan_artifact(cache_path, artifact_name, payload)

            self._send_success(
                {
                    "project": project.as_json(),
                    "artifacts": tuple(sorted(artifacts)),
                    "node_count": len(graph.nodes),
                    "edge_count": len(graph.edges),
                }
            )
        except (CachePathError, OSError, ProjectPathError) as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "rescan_failed", str(exc))

    def _handle_files_tree(self) -> None:
        project, cache_path = self._current_project_and_cache()
        if project is None or cache_path is None:
            return

        try:
            artifact = read_quick_scan_artifact(cache_path, "files_tree")
            self._send_success(artifact or self._empty_files_tree(project))
        except (CachePathError, OSError, json.JSONDecodeError) as exc:
            self._send_failure(HTTPStatus.INTERNAL_SERVER_ERROR, "cache_read_failed", str(exc))

    def _handle_file_detail(self, query: dict[str, list[str]]) -> None:
        project, cache_path = self._current_project_and_cache()
        if project is None or cache_path is None:
            return

        requested = query.get("path", [""])[0]
        try:
            file_path, relative_path = self._resolve_project_file(project.path, requested)
            if not file_path.exists() or not file_path.is_file():
                self._send_failure(HTTPStatus.NOT_FOUND, "file_not_found", "file was not found")
                return

            stat_result = file_path.stat()
            max_bytes = 65536
            raw = file_path.read_bytes()[:max_bytes]
            self._send_success(
                {
                    "path": relative_path,
                    "name": file_path.name,
                    "size_bytes": stat_result.st_size,
                    "content_text": raw.decode("utf-8", errors="replace"),
                    "encoding": "utf-8",
                    "truncated": stat_result.st_size > max_bytes,
                    "insight": self._insight_for_path(cache_path, relative_path),
                }
            )
        except ProjectPathError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "unsafe_path", str(exc))
        except OSError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "file_read_failed", str(exc))

    def _insight_for_path(self, cache_path: CachePath, relative_path: str) -> dict[str, Any] | None:
        try:
            artifact = read_quick_scan_artifact(cache_path, "file_insights")
        except (CachePathError, OSError, json.JSONDecodeError):
            return None
        for item in list((artifact or {}).get("items") or []):
            if isinstance(item, dict) and item.get("path") == relative_path:
                return item
        return None

    def _handle_cached_artifact(self, artifact_name: str, empty_factory: Any) -> None:
        project, cache_path = self._current_project_and_cache()
        if project is None or cache_path is None:
            return

        try:
            artifact = read_quick_scan_artifact(cache_path, artifact_name)
            self._send_success(artifact or empty_factory(project))
        except (CachePathError, OSError, json.JSONDecodeError) as exc:
            self._send_failure(HTTPStatus.INTERNAL_SERVER_ERROR, "cache_read_failed", str(exc))

    def _handle_git_timeline(self, query: dict[str, list[str]]) -> None:
        client = self._git_client_or_none()
        if client is None:
            return
        try:
            path = self._optional_query_value(query, "path")
            self._send_success(get_timeline(client, selected_file=path))
        except GitClientError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "bad_git_request", str(exc))
        except GitTimeoutError as exc:
            self._send_failure(HTTPStatus.GATEWAY_TIMEOUT, "git_timeout", str(exc))
        except GitCommandError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "git_command_failed", str(exc))

    def _handle_git_commit(self, query: dict[str, list[str]]) -> None:
        client = self._git_client_or_none()
        if client is None:
            return
        try:
            commit_hash = self._required_query_value(query, "hash")
            self._send_success(get_commit_detail(client, commit_hash))
        except GitClientError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "bad_git_request", str(exc))
        except GitTimeoutError as exc:
            self._send_failure(HTTPStatus.GATEWAY_TIMEOUT, "git_timeout", str(exc))
        except GitCommandError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "git_command_failed", str(exc))

    def _handle_git_diff(self, query: dict[str, list[str]]) -> None:
        client = self._git_client_or_none()
        if client is None:
            return
        try:
            commit_hash = self._required_query_value(query, "hash")
            path = self._optional_query_value(query, "path")
            self._send_success(get_commit_diff(client, commit_hash, path=path))
        except GitClientError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "bad_git_request", str(exc))
        except GitTimeoutError as exc:
            self._send_failure(HTTPStatus.GATEWAY_TIMEOUT, "git_timeout", str(exc))
        except GitCommandError as exc:
            self._send_failure(HTTPStatus.BAD_REQUEST, "git_command_failed", str(exc))

    def _git_client_or_none(self) -> GitClient | None:
        project = self.server.state.current_project
        if project is None:
            self._send_failure(HTTPStatus.CONFLICT, "no_project", "open a project before requesting git data")
            return None
        return GitClient(str(project.path))

    def _required_query_value(self, query: dict[str, list[str]], name: str) -> str:
        value = self._optional_query_value(query, name)
        if value is None:
            raise GitClientError(f"{name} is required")
        return value

    def _optional_query_value(self, query: dict[str, list[str]], name: str) -> str | None:
        values = query.get(name)
        if values is None:
            return None
        if len(values) != 1:
            raise GitClientError(f"{name} must be supplied at most once")
        value = values[0]
        if value == "":
            raise GitClientError(f"{name} must not be empty")
        return value

    def _current_project_and_cache(self) -> tuple[ProjectRoot | None, CachePath | None]:
        project = self.server.state.current_project
        cache_path = self.server.state.cache_path
        if project is None or cache_path is None:
            self._send_failure(HTTPStatus.CONFLICT, "no_project", "no project is open")
            return None, None
        return project, cache_path

    def _graph_with_folder_edges(self, graph: GraphData) -> GraphData:
        folder_graph = build_folder_view(graph.project_hash, graph.nodes)
        return GraphData(
            project_hash=graph.project_hash,
            generated_at=graph.generated_at,
            nodes=graph.nodes,
            edges=folder_graph.edges,
            metadata={**graph.metadata, "view": "folder", "source": "quick_scan"},
        )

    def _files_tree_from_graph(self, project: ProjectRoot, graph: GraphData) -> dict[str, Any]:
        children_by_folder: dict[str, list[dict[str, Any]]] = {}
        folders_by_id: dict[str, FolderNode] = {}
        for node in graph.nodes:
            if isinstance(node, FolderNode):
                folders_by_id[node.id] = node
                children_by_folder.setdefault(node.id, [])

        for node in graph.nodes:
            if isinstance(node, FolderNode) and node.parent is not None:
                children_by_folder.setdefault(node.parent, []).append(self._folder_tree_node(node))
            if isinstance(node, FileNode):
                children_by_folder.setdefault(node.folder, []).append(
                    {
                        "type": "file",
                        "path": node.path,
                        "name": Path(node.path).name,
                        "id": node.id,
                        "language": node.language,
                        "role": node.role,
                        "summary_status": node.summary_status,
                    }
                )

        root_folder = folders_by_id.get("folder:.")
        root = self._folder_tree_node(root_folder) if root_folder is not None else self._empty_files_tree(project)["root"]
        root["name"] = project.display_name
        self._attach_tree_children(root, children_by_folder)
        return {"project_hash": project.project_hash, "root": root}

    def _folder_tree_node(self, node: FolderNode | None) -> dict[str, Any]:
        path = "" if node is None else node.path
        return {
            "type": "folder",
            "path": path,
            "name": Path(path).name if path else "",
            "id": "folder:." if node is None else node.id,
            "capture_children": True if node is None else node.capture_children,
            "collapsed": False if node is None else node.collapsed,
            "volatile": False if node is None else node.volatile,
            "children": [],
        }

    def _attach_tree_children(self, root: dict[str, Any], children_by_folder: dict[str, list[dict[str, Any]]]) -> None:
        folders = [root]
        while folders:
            current = folders.pop()
            children = sorted(
                children_by_folder.get(str(current["id"]), []),
                key=lambda child: (child["type"] != "folder", str(child["name"])),
            )
            current["children"] = children
            folders.extend(child for child in children if child["type"] == "folder")

    def _resolve_project_file(self, project_root: Path, requested: str) -> tuple[Path, str]:
        relative = Path(requested)
        if not requested or relative.is_absolute() or ".." in relative.parts:
            raise ProjectPathError(f"unsafe project-relative path: {requested}")
        candidate = project_root / relative
        safe_relative = safe_project_relative_path(project_root, candidate)
        return candidate.resolve(strict=False), safe_relative

    def _empty_files_tree(self, project: ProjectRoot) -> dict[str, Any]:
        return {
            "project_hash": project.project_hash,
            "root": {
                "type": "folder",
                "path": "",
                "name": project.display_name,
                "id": "folder:.",
                "children": [],
            },
        }

    def _empty_graph_data(self, project: ProjectRoot) -> dict[str, Any]:
        return {"project_hash": project.project_hash, "generated_at": None, "nodes": [], "edges": [], "metadata": {}}

    def _empty_layouts(self, project: ProjectRoot) -> dict[str, Any]:
        return {"layouts": {}, "manifest": {"project_graph_hash": project.project_hash, "computed_at": None}}

    def _empty_render_index(self, _project: ProjectRoot) -> dict[str, Any]:
        return {"visible_edges_by_view": {}, "edge_index_by_relation_tag": {}, "style_tokens_by_encoding": {}}

    def _empty_edge_routes(self, _project: ProjectRoot) -> dict[str, Any]:
        return {"routes": []}

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        if not raw:
            return {}
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            raise json.JSONDecodeError("expected JSON object", raw.decode("utf-8", errors="replace"), 0)
        return data

    def _send_success(self, data: Any) -> None:
        self._send_json(HTTPStatus.OK, ApiResponse.success(data))

    def _send_failure(self, status: HTTPStatus, code: str, message: str) -> None:
        self._send_json(status, ApiResponse.failure(code, message))

    def _send_json(self, status: HTTPStatus, response: ApiResponse[Any]) -> None:
        body = _response_payload(response)
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _handle_static_asset(self, route: str) -> None:
        relative = unquote(route.removeprefix("/static/"))
        if not relative or relative.startswith("/") or ".." in Path(relative).parts:
            self._send_failure(HTTPStatus.NOT_FOUND, "not_found", "unknown static asset")
            return

        asset_path = (STATIC_ROOT / relative).resolve()
        try:
            asset_path.relative_to(STATIC_ROOT.resolve())
        except ValueError:
            self._send_failure(HTTPStatus.NOT_FOUND, "not_found", "unknown static asset")
            return

        self._send_static_file(asset_path)

    def _send_static_file(self, path: Path) -> None:
        if not path.is_file():
            self._send_failure(HTTPStatus.NOT_FOUND, "not_found", "unknown static asset")
            return

        body = path.read_bytes()
        content_type, _encoding = mimetypes.guess_type(path.name)
        if content_type is None:
            content_type = "application/octet-stream"

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)
