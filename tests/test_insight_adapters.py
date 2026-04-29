from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.contracts.models import CachePath, SummaryStatus
from mizuchi.insight import (
    CacheInsightArtifactStore,
    FallbackFileInsightAdapter,
    classify_file_domain_tag,
    domain_fallback_role,
    file_insight_result_to_payload,
)


class InsightAdapterTests(TestCase):
    def test_fallback_file_insight_adapter_returns_lightweight_placeholders(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = FallbackFileInsightAdapter().inspect_file(root, "tests/test_app.py")

        self.assertEqual(result.path, "tests/test_app.py")
        self.assertEqual(result.evidence[0].file, "tests/test_app.py")
        self.assertEqual(result.evidence[0].kind, "source_file")
        self.assertEqual(result.evidence[1].kind, "role_hint")
        self.assertIs(result.summary.status, SummaryStatus.READY)
        self.assertIn("Python test file", result.summary.text)
        self.assertEqual(result.role.role, "test")
        self.assertGreater(result.role.confidence, 0.8)
        self.assertEqual(result.issues, ())

    def test_fallback_role_inference_covers_common_project_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            adapter = FallbackFileInsightAdapter()
            cases = {
                "README.md": "documentation",
                "pyproject.toml": "configuration",
                ".github/workflows/ci.yml": "ci",
                "Dockerfile": "container",
                "src/main.py": "entrypoint",
                "src/api/client.ts": "api",
                "src/state/store.ts": "state",
                "assets/logo.svg": "asset",
                "src/styles.css": "style",
                "src/models/user.json": "schema",
            }

            for relative_path, expected_role in cases.items():
                self.assertEqual(adapter.infer_role(root, relative_path).role, expected_role)

    def test_file_insight_result_payload_is_json_ready(self) -> None:
        with TemporaryDirectory() as temp_dir:
            result = FallbackFileInsightAdapter().inspect_file(Path(temp_dir), "src/app.py")
            payload = file_insight_result_to_payload(result)

        self.assertEqual(payload["path"], "src/app.py")
        self.assertEqual(payload["summary"]["status"], "ready")
        self.assertEqual(payload["summary"]["sections"][0]["section_key"], "identity")
        self.assertEqual(payload["role"]["role"], "entrypoint")
        self.assertEqual(
            payload["evidence"][0],
            {"file": "src/app.py", "line": None, "text": "project-relative file", "kind": "source_file"},
        )

    def test_domain_helpers_match_adapted_kuchinawa_shape(self) -> None:
        self.assertEqual(classify_file_domain_tag("tests/test_api.py"), "testing")
        self.assertEqual(classify_file_domain_tag("src/api/client.ts"), "api_integration")
        self.assertEqual(domain_fallback_role("api_integration"), "api")

    def test_cache_artifact_store_targets_cache_project_dir(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            cache_path = CachePath(root=root / ".mizuchi-cache", project_hash="abc123")
            store = CacheInsightArtifactStore(cache_path, project_root=root / "project")

            ref = store.artifact_ref("src/app.py")

        self.assertEqual(ref.project_hash, "abc123")
        self.assertEqual(ref.relative_path, "src/app.py")
        self.assertEqual(ref.artifact_path, cache_path.project_dir / "insight" / "src__app.py.json")

    def test_cache_artifact_store_rejects_cache_inside_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir) / "project"
            project_root.mkdir()
            cache_path = CachePath(root=project_root / ".mizuchi", project_hash="abc123")

            with self.assertRaises(ValueError):
                CacheInsightArtifactStore(cache_path, project_root=project_root)

    def test_cache_artifact_store_rejects_unsafe_relative_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            cache_path = CachePath(root=Path(temp_dir) / "cache", project_hash="abc123")
            store = CacheInsightArtifactStore(cache_path)

            with self.assertRaises(ValueError):
                store.artifact_ref("../secret.py")
