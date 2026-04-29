from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.security.paths import PathSafetyError, project_relative_path, resolve_project_path


class PathSafetyTests(TestCase):
    def test_resolve_project_path_allows_project_relative(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()

            self.assertEqual(resolve_project_path(root, "src/app.py"), (root / "src" / "app.py").resolve())

    def test_resolve_project_path_rejects_escape(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            root.mkdir()

            with self.assertRaises(PathSafetyError):
                resolve_project_path(root, "../outside.txt")

    def test_project_relative_path_normalizes_safe_absolute_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repo"
            file_path = root / "src" / "app.py"
            file_path.parent.mkdir(parents=True)
            file_path.write_text("", encoding="utf-8")

            self.assertEqual(project_relative_path(root, file_path), "src/app.py")
