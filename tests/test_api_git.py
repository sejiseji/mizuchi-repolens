from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from mizuchi.api.server import LOCAL_HOST, create_server
from mizuchi.contracts.models import DiffResult, ProjectRoot
from mizuchi.git import validate_commit_hash, validate_relative_path
from mizuchi.git.timeline import FIELD_SEP, LOG_FORMAT
from mizuchi.runtime.state import RuntimeState


def _request_json(url: str) -> tuple[int, dict[str, object]]:
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read().decode("utf-8"))
        finally:
            exc.close()


class GitApiTests(TestCase):
    def test_git_timeline_uses_current_project_and_validated_path_filter(self) -> None:
        with _running_git_server() as server:
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"

            status, payload = _request_json(f"{base_url}/api/git/timeline?path=src/app.py")

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        data = payload["data"]
        assert isinstance(data, list)
        self.assertEqual(data[0]["commit_hash"], "a" * 40)
        self.assertTrue(data[0]["selected_file_touched"])
        self.assertEqual(
            RecordingGitClient.instances[0].calls[0],
            (
                "log",
                ["-n50", "--date=iso-strict", f"--pretty=format:{LOG_FORMAT}", "--numstat", "--", "src/app.py"],
            ),
        )

    def test_git_commit_preserves_hash_validation(self) -> None:
        with _running_git_server() as server:
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"

            status, payload = _request_json(f"{base_url}/api/git/commit?hash=HEAD")

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])
        error = payload["error"]
        assert isinstance(error, dict)
        self.assertEqual(error["code"], "bad_git_request")
        self.assertEqual(RecordingGitClient.instances[0].calls, [])

    def test_git_commit_returns_detail(self) -> None:
        with _running_git_server() as server:
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"

            status, payload = _request_json(f"{base_url}/api/git/commit?hash={'b' * 40}")

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        data = payload["data"]
        assert isinstance(data, dict)
        self.assertEqual(data["changed_files"], ["src/app.py", "tests/test_app.py"])
        self.assertEqual(data["body"], "Body line")

    def test_git_diff_returns_truncation_fields_and_validates_path(self) -> None:
        with _running_git_server() as server:
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"

            status, payload = _request_json(f"{base_url}/api/git/diff?hash={'c' * 40}&path=../secret")

        self.assertEqual(status, 400)
        self.assertFalse(payload["ok"])

        with _running_git_server() as server:
            base_url = f"http://{LOCAL_HOST}:{server.server_port}"
            status, payload = _request_json(f"{base_url}/api/git/diff?hash={'c' * 40}&path=src/app.py")

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        data = payload["data"]
        assert isinstance(data, dict)
        self.assertEqual(data["path"], "src/app.py")
        self.assertTrue(data["truncated"])
        self.assertEqual(data["max_bytes"], 200000)

    def test_git_api_requires_open_project(self) -> None:
        server = create_server(0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            status, payload = _request_json(f"http://{LOCAL_HOST}:{server.server_port}/api/git/timeline")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])


class RecordingGitClient:
    instances: list["RecordingGitClient"] = []

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path
        self.calls: list[tuple[str, list[str]]] = []
        self.instances.append(self)

    def log(self, args: list[str]) -> str:
        self.calls.append(("log", args))
        return "\n".join(
            [
                FIELD_SEP.join(["a" * 40, "aaaaaaa", "2026-04-29T01:02:03+00:00", "Ada", "Touch app"]),
                "1\t2\tsrc/app.py",
            ]
        )

    def show(self, args: list[str]) -> str:
        self.calls.append(("show", args))
        return "\n".join(
            [
                FIELD_SEP.join(["b" * 40, "bbbbbbb", "2026-04-29T01:02:03+00:00", "Ben", "Detail", "Body line"]),
                "",
                "src/app.py",
                "tests/test_app.py",
            ]
        )

    def diff_result(self, commit_hash: str, path: str | None = None, max_bytes: int = 200_000) -> DiffResult:
        commit_hash = validate_commit_hash(commit_hash)
        path = validate_relative_path(path)
        self.calls.append(("diff_result", [commit_hash, path or "", str(max_bytes)]))
        return DiffResult(
            commit_hash=commit_hash,
            path=path,
            diff_text="diff --git a/src/app.py b/src/app.py\n...",
            truncated=True,
            max_bytes=max_bytes,
        )


class _running_git_server:
    def __enter__(self):
        RecordingGitClient.instances.clear()
        self.temp_dir = TemporaryDirectory()
        project_path = Path(self.temp_dir.name) / "repo"
        project_path.mkdir()
        state = RuntimeState(
            current_project=ProjectRoot(
                path=project_path,
                display_name="repo",
                project_hash="abc123",
                is_git_repo=True,
                opened_at=datetime.now(timezone.utc),
            )
        )
        self.patcher = patch("mizuchi.api.server.GitClient", RecordingGitClient)
        self.patcher.start()
        self.server = create_server(0, state=state)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self.server

    def __exit__(self, exc_type, exc, tb) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.patcher.stop()
        self.temp_dir.cleanup()
