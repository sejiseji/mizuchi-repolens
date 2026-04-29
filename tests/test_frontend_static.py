from __future__ import annotations

import threading
import urllib.error
import urllib.request
from pathlib import Path
from unittest import TestCase

from mizuchi.api.server import LOCAL_HOST, create_server


STATIC_ROOT = Path(__file__).resolve().parents[1] / "mizuchi" / "static"


def _request(url: str) -> tuple[int, str, bytes]:
    with urllib.request.urlopen(url, timeout=5) as response:
        return response.status, response.headers.get("Content-Type", ""), response.read()


class FrontendStaticTests(TestCase):
    def test_frontend_assets_exist(self) -> None:
        self.assertTrue((STATIC_ROOT / "index.html").is_file())
        self.assertTrue((STATIC_ROOT / "styles.css").is_file())
        self.assertTrue((STATIC_ROOT / "app.js").is_file())

        index = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("Open", index)
        self.assertIn("Rescan", index)
        self.assertIn("Shutdown", index)
        self.assertIn("Project current status", index)
        self.assertIn("File Tree", index)
        self.assertIn("file-tree-view", index)
        self.assertIn("file-tree-filter", index)
        self.assertIn("clear-tree-filter", index)
        self.assertIn("Graph", index)
        self.assertIn("graph-canvas", index)
        self.assertIn("graph-zoom-in", index)
        self.assertIn("graph-selected", index)
        self.assertIn("JSON debug", index)
        self.assertIn("File Detail", index)
        self.assertIn("Git Timeline", index)
        self.assertIn("git-selected-state", index)
        self.assertIn("git-timeline-list", index)
        self.assertIn("Diff", index)
        self.assertIn("git-diff-summary", index)
        self.assertIn("git-diff-hunks", index)
        self.assertIn("git-diff-view", index)

    def test_server_serves_frontend_shell_and_assets(self) -> None:
        server = create_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://{LOCAL_HOST}:{server.server_port}"

        try:
            index_status, index_type, index_body = _request(f"{base_url}/")
            css_status, css_type, css_body = _request(f"{base_url}/static/styles.css")
            js_status, js_type, js_body = _request(f"{base_url}/static/app.js")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(index_status, 200)
        self.assertIn("text/html", index_type)
        self.assertIn(b"Mizuchi RepoLens", index_body)
        self.assertEqual(css_status, 200)
        self.assertIn("text/css", css_type)
        self.assertIn(b".workspace", css_body)
        self.assertIn(b".tree-view", css_body)
        self.assertIn(b".tree-filter-controls", css_body)
        self.assertIn(b".timeline-list", css_body)
        self.assertIn(b".timeline-selected-label", css_body)
        self.assertIn(b".diff-view", css_body)
        self.assertIn(b".diff-truncated-banner", css_body)
        self.assertIn(b".diff-hunk-button", css_body)
        self.assertIn(b".graph-canvas", css_body)
        self.assertIn(b"touch-action: none", css_body)
        self.assertEqual(js_status, 200)
        self.assertIn("javascript", js_type)
        self.assertIn(b"/api/project/open", js_body)
        self.assertIn(b"renderFileTreeData", js_body)
        self.assertIn(b"renderFilteredFileTree", js_body)
        self.assertIn(b"No files match", js_body)
        self.assertIn(b"renderGraphVisualization", js_body)
        self.assertIn(b"handleGraphWheel", js_body)
        self.assertIn(b"startGraphDrag", js_body)
        self.assertIn(b"renderTimelineData", js_body)
        self.assertIn(b"renderDiffData", js_body)
        self.assertIn(b"updateTimelineSelection", js_body)
        self.assertIn(b"scrollIntoView", js_body)

    def test_static_serving_rejects_traversal(self) -> None:
        server = create_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://{LOCAL_HOST}:{server.server_port}"

        try:
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(f"{base_url}/static/%2e%2e/api/server.py", timeout=5)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        try:
            self.assertEqual(raised.exception.code, 404)
        finally:
            raised.exception.close()
