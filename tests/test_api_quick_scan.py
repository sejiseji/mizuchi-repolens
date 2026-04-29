from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.api.server import LOCAL_HOST, create_server
from mizuchi.runtime.state import RuntimeState


def _request_json(url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        finally:
            exc.close()


class QuickScanApiTests(TestCase):
    def test_rescan_writes_graph_artifacts_and_file_tree(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            cache_root = tmp_path / "cache"
            (project / "src").mkdir(parents=True)
            (project / "src" / "app.py").write_text("print('hello')\n", encoding="utf-8")
            (project / "README.md").write_text("# Demo\n", encoding="utf-8")

            state = RuntimeState()
            state.open_project(project, cache_root=cache_root)
            server, thread, base_url = self._start_server(state)

            try:
                rescan = _request_json(f"{base_url}/api/project/rescan", {})
                tree = _request_json(f"{base_url}/api/files/tree")
                graph = _request_json(f"{base_url}/api/graph/data")
                layouts = _request_json(f"{base_url}/api/graph/layouts")
                render_index = _request_json(f"{base_url}/api/graph/render-index")
                edge_routes = _request_json(f"{base_url}/api/graph/edge-routes")
            finally:
                self._stop_server(server, thread)

            self.assertTrue(rescan["ok"])
            self.assertTrue(tree["ok"])
            self.assertTrue(graph["ok"])
            self.assertTrue(layouts["ok"])
            self.assertTrue(render_index["ok"])
            self.assertTrue(edge_routes["ok"])

            graph_data = graph["data"]
            assert isinstance(graph_data, dict)
            self.assertGreaterEqual(len(graph_data["nodes"]), 3)
            self.assertGreaterEqual(len(graph_data["edges"]), 2)

            tree_data = tree["data"]
            assert isinstance(tree_data, dict)
            root = tree_data["root"]
            assert isinstance(root, dict)
            self.assertEqual(root["name"], "repo")
            self.assertTrue((cache_root / state.current_project.project_hash / "quick_scan" / "graph_data.json").is_file())
            self.assertTrue((cache_root / state.current_project.project_hash / "quick_scan" / "quick_scan.json").is_file())
            self.assertTrue((cache_root / state.current_project.project_hash / "quick_scan" / "file_inventory.json").is_file())
            self.assertTrue((cache_root / state.current_project.project_hash / "quick_scan" / "file_insights.json").is_file())

    def test_file_detail_rejects_traversal_and_reads_project_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            project.mkdir()
            (project / "app.py").write_text("value = 1\n", encoding="utf-8")

            state = RuntimeState()
            state.open_project(project, cache_root=tmp_path / "cache")
            server, thread, base_url = self._start_server(state)

            try:
                _request_json(f"{base_url}/api/project/rescan", {})
                detail = _request_json(f"{base_url}/api/files/detail?path=app.py")
                traversal = _request_json(f"{base_url}/api/files/detail?path=../secret.txt")
            finally:
                self._stop_server(server, thread)

            self.assertTrue(detail["ok"])
            data = detail["data"]
            assert isinstance(data, dict)
            self.assertEqual(data["path"], "app.py")
            self.assertEqual(data["content_text"], "value = 1\n")
            self.assertEqual(data["insight"]["path"], "app.py")
            self.assertEqual(data["insight"]["summary"]["status"], "ready")
            self.assertFalse(traversal["ok"])
            error = traversal["error"]
            assert isinstance(error, dict)
            self.assertEqual(error["code"], "unsafe_path")

    def test_graph_endpoint_errors_when_no_project_is_open(self) -> None:
        server, thread, base_url = self._start_server(RuntimeState())

        try:
            response = _request_json(f"{base_url}/api/graph/data")
        finally:
            self._stop_server(server, thread)

        self.assertFalse(response["ok"])
        error = response["error"]
        assert isinstance(error, dict)
        self.assertEqual(error["code"], "no_project")

    def test_graph_endpoint_returns_empty_payload_before_rescan(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            project.mkdir()
            state = RuntimeState()
            state.open_project(project, cache_root=tmp_path / "cache")
            server, thread, base_url = self._start_server(state)

            try:
                response = _request_json(f"{base_url}/api/graph/data")
            finally:
                self._stop_server(server, thread)

            self.assertTrue(response["ok"])
            data = response["data"]
            assert isinstance(data, dict)
            self.assertEqual(data["nodes"], [])
            self.assertEqual(data["edges"], [])

    def _start_server(self, state: RuntimeState) -> tuple[object, threading.Thread, str]:
        server = create_server(0, state)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{LOCAL_HOST}:{server.server_port}"

    def _stop_server(self, server: object, thread: threading.Thread) -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
