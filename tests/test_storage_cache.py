from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.storage.cache import (
    CachePathError,
    quick_scan_artifact_path,
    read_quick_scan_artifact,
    resolve_cache_path,
    write_quick_scan_artifact,
)


class CachePathTests(TestCase):
    def test_resolve_cache_path_uses_external_namespace(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            cache_root = tmp_path / "cache" / "mizuchi-repolens"
            project.mkdir()

            cache = resolve_cache_path(project, "abc123", cache_root=cache_root)

            self.assertEqual(cache.root, cache_root.resolve())
            self.assertEqual(cache.project_dir, cache_root.resolve() / "abc123")

    def test_resolve_cache_path_rejects_cache_inside_project(self) -> None:
        with TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "repo"
            project.mkdir()

            with self.assertRaises(CachePathError):
                resolve_cache_path(project, "abc123", cache_root=project / ".mizuchi")

    def test_quick_scan_artifact_round_trip_stays_under_cache(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            cache_root = tmp_path / "cache"
            project.mkdir()
            cache = resolve_cache_path(project, "abc123", cache_root=cache_root)

            path = write_quick_scan_artifact(cache, "graph_data", {"nodes": [], "edges": []})

            self.assertEqual(read_quick_scan_artifact(cache, "graph_data"), {"nodes": [], "edges": []})
            self.assertEqual(path, quick_scan_artifact_path(cache, "graph_data"))
            self.assertIn(cache.project_dir, path.parents)

    def test_quick_scan_artifact_rejects_unknown_names(self) -> None:
        with TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            project = tmp_path / "repo"
            project.mkdir()
            cache = resolve_cache_path(project, "abc123", cache_root=tmp_path / "cache")

            with self.assertRaises(CachePathError):
                quick_scan_artifact_path(cache, "../escape")
