from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.contracts.models import FileNode, FolderNode
from mizuchi.project import (
    ProjectPathError,
    ProjectRootError,
    build_quick_scan_graph,
    inventory_to_payload,
    path_tokens,
    safe_project_relative_path,
    scan_project_inventory,
    validate_project_root,
)


class ProjectInventoryTests(TestCase):
    def test_validate_project_root_uses_read_only_identity(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

            project = validate_project_root(root)

            self.assertEqual(project.path, root.resolve())
            self.assertEqual(project.display_name, root.name)
            self.assertEqual(len(project.project_hash), 16)
            self.assertFalse(project.is_git_repo)

    def test_validate_project_root_rejects_files(self) -> None:
        with TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "not-a-root.txt"
            file_path.write_text("x", encoding="utf-8")

            with self.assertRaises(ProjectRootError):
                validate_project_root(file_path)

    def test_safe_project_relative_path_rejects_outside_paths(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            outside = root.parent / "outside.txt"

            with self.assertRaises(ProjectPathError):
                safe_project_relative_path(root, outside)

    def test_inventory_captures_default_policy_without_descending_volatile_dirs(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")
            (root / "node_modules").mkdir()
            (root / "node_modules" / "leftpad.js").write_text("module.exports = 1\n", encoding="utf-8")

            inventory = scan_project_inventory(root)

        self.assertEqual([file.path for file in inventory.files], ["src/app.py"])
        folders = {folder.path: folder for folder in inventory.folders}
        self.assertTrue(folders[""].capture_children)
        self.assertTrue(folders["src"].capture_children)
        self.assertFalse(folders["node_modules"].capture_children)
        self.assertTrue(folders["node_modules"].collapsed)
        self.assertTrue(folders["node_modules"].volatile)

    def test_quick_scan_graph_uses_shared_file_and_folder_nodes(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs").mkdir()
            (root / "docs" / "README.md").write_text("# Demo\n", encoding="utf-8")

            graph = build_quick_scan_graph(str(root))

        self.assertTrue(graph.metadata["read_only"])
        self.assertEqual(graph.metadata["file_count"], 1)
        self.assertTrue(any(isinstance(node, FolderNode) and node.path == "docs" for node in graph.nodes))
        file_nodes = [node for node in graph.nodes if isinstance(node, FileNode)]
        self.assertEqual(len(file_nodes), 1)
        self.assertEqual(file_nodes[0].path, "docs/README.md")
        self.assertEqual(file_nodes[0].folder, "folder:docs")
        self.assertEqual(file_nodes[0].language, "Markdown")

    def test_inventory_payload_is_json_ready_and_stable(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "api-client.py").write_text("print('hi')\n", encoding="utf-8")

            inventory = scan_project_inventory(root)
            payload = inventory_to_payload(inventory)

        self.assertEqual(payload["schema_version"], "mizuchi_project_inventory_v0_2")
        self.assertEqual(payload["file_count"], 1)
        self.assertEqual(payload["files"][0]["path"], "src/api-client.py")
        self.assertEqual(payload["files"][0]["path_tokens"], ["src", "api-client", "api", "client"])
        self.assertEqual(payload["folders"][0]["path"], "")

    def test_path_tokens_deduplicates_path_parts_and_stem_chunks(self) -> None:
        self.assertEqual(path_tokens("src/state-store/state_store.py"), ("src", "state-store", "state_store", "state", "store"))
