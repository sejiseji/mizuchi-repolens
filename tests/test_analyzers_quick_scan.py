from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from mizuchi.analyzers import quick_scan_project, quick_scan_result_to_payload
from mizuchi.contracts.models import FileNode, SummaryStatus


class QuickScanAnalyzerTests(TestCase):
    def test_quick_scan_project_applies_fallback_roles(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "tests").mkdir()
            (root / "tests" / "test_demo.py").write_text("def test_demo(): pass\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")

            result = quick_scan_project(root)

        files = {node.path: node for node in result.graph.nodes if isinstance(node, FileNode)}
        self.assertEqual(files["tests/test_demo.py"].role, "test")
        self.assertIs(files["tests/test_demo.py"].summary_status, SummaryStatus.READY)
        self.assertEqual(files["pyproject.toml"].role, "configuration")
        self.assertEqual(len(result.insights), 2)

    def test_quick_scan_result_payload_includes_inventory_and_insights(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hi')\n", encoding="utf-8")

            result = quick_scan_project(root)
            payload = quick_scan_result_to_payload(result)

        self.assertEqual(payload["schema_version"], "mizuchi_quick_scan_v0_2")
        self.assertEqual(payload["graph"]["metadata"]["insight_adapter"], "fallback")
        self.assertEqual(payload["inventory"]["files"][0]["path"], "src/main.py")
        self.assertEqual(payload["insights"][0]["role"]["role"], "entrypoint")
        self.assertEqual(payload["insights"][0]["summary"]["status"], "ready")
