from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.api.server import LOCAL_HOST, create_server
from mizuchi.runtime.state import RuntimeState


def _request_json(url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


class RuntimeApiTests(TestCase):
    def test_runtime_state_open_project_keeps_cache_outside_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            cache_root = tmp_path / "cache"
            project.mkdir()

            state = RuntimeState()
            opened = state.open_project(project, cache_root=cache_root)

            self.assertEqual(opened.path, project.resolve())
            self.assertIsNotNone(state.cache_path)
            assert state.cache_path is not None
            self.assertNotIn(project.resolve(), state.cache_path.project_dir.parents)

    def test_api_status_and_open_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "repo"
            project.mkdir()
            server = create_server(0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"

            try:
                status = _request_json(f"{base_url}/api/app/status")
                opened = _request_json(f"{base_url}/api/project/open", {"path": str(project)})
                current = _request_json(f"{base_url}/api/project/current")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)

            self.assertTrue(status["ok"])
            self.assertEqual(status["data"], {"status": "ok", "local_only": True})
            self.assertTrue(opened["ok"])
            self.assertTrue(current["ok"])
            data = current["data"]
            assert isinstance(data, dict)
            project_data = data["project"]
            assert isinstance(project_data, dict)
            self.assertEqual(project_data["path"], str(project.resolve()))
