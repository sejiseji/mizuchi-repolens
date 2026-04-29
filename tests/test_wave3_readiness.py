from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
from unittest import TestCase


REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC_ROOT = REPO_ROOT / "mizuchi" / "static"


class _SemanticHookParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.classes: set[str] = set()
        self.data_hooks: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del tag
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.add(value)
            elif name == "class":
                self.classes.update(part for part in value.split() if part)
            elif name.startswith("data-"):
                self.data_hooks.add(f"{name}={value}")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class Wave3ReadinessTests(TestCase):
    def test_static_assets_keep_stable_graph_mount_points(self) -> None:
        index_path = STATIC_ROOT / "index.html"
        styles_path = STATIC_ROOT / "styles.css"
        app_path = STATIC_ROOT / "app.js"

        for path in (index_path, styles_path, app_path):
            with self.subTest(path=path.relative_to(REPO_ROOT)):
                self.assertTrue(path.is_file(), f"missing static asset: {path.relative_to(REPO_ROOT)}")

        parser = _SemanticHookParser()
        parser.feed(_read(index_path))
        app_js = _read(app_path)
        styles_css = _read(styles_path)

        self.assertIn("graph-view", parser.ids)
        self.assertIn("file-tree-view", parser.ids)
        self.assertIn("file-tree-filter", parser.ids)
        self.assertIn("clear-tree-filter", parser.ids)
        self.assertIn("git-selected-state", parser.ids)
        self.assertIn("git-timeline-list", parser.ids)
        self.assertIn("git-diff-summary", parser.ids)
        self.assertIn("git-diff-hunks", parser.ids)
        self.assertIn("git-diff-view", parser.ids)
        self.assertIn("graph-panel", parser.classes)
        self.assertIn('document.querySelector("#graph-view")', app_js)
        self.assertIn("/api/graph/data", app_js)
        self.assertIn("renderFileTreeData", app_js)
        self.assertIn("renderFilteredFileTree", app_js)
        self.assertIn("renderTimelineData", app_js)
        self.assertIn("renderDiffData", app_js)
        self.assertIn("updateTimelineSelection", app_js)
        self.assertIn("handleGraphWheel", app_js)
        self.assertIn("startGraphDrag", app_js)
        self.assertIn(".graph-panel", styles_css)
        self.assertIn(".graph-canvas.is-dragging", styles_css)
        self.assertIn(".tree-filter-controls", styles_css)
        self.assertIn(".diff-truncated-banner", styles_css)

    def test_docs_smoke_artifacts_are_checkable_when_present(self) -> None:
        docs_to_requirements = {
            REPO_ROOT / "README.md": ("Mizuchi RepoLens", "static", "smoke"),
            REPO_ROOT / "docs" / "browser_smoke_test.md": ("browser", "localhost", "Graph"),
        }

        missing = [path.relative_to(REPO_ROOT).as_posix() for path in docs_to_requirements if not path.is_file()]
        if missing:
            self.skipTest(f"Wave 3 docs not integrated yet: {', '.join(missing)}")

        for path, required_terms in docs_to_requirements.items():
            text = _read(path)
            with self.subTest(path=path.relative_to(REPO_ROOT).as_posix()):
                for term in required_terms:
                    self.assertIn(term, text)

    def test_wave3_graph_debug_hooks_are_semantic_when_integrated(self) -> None:
        asset_paths = [STATIC_ROOT / "index.html", STATIC_ROOT / "app.js", STATIC_ROOT / "styles.css"]
        missing = [path.relative_to(REPO_ROOT).as_posix() for path in asset_paths if not path.is_file()]
        if missing:
            self.skipTest(f"static assets not available: {', '.join(missing)}")

        index_html = _read(STATIC_ROOT / "index.html")
        app_js = _read(STATIC_ROOT / "app.js")
        styles_css = _read(STATIC_ROOT / "styles.css")
        combined = "\n".join((index_html, app_js, styles_css))

        parser = _SemanticHookParser()
        parser.feed(index_html)
        semantic_hooks = parser.ids | parser.classes | parser.data_hooks
        graph_hooks = {hook for hook in semantic_hooks if "graph" in hook.lower()}
        debug_hooks = {hook for hook in semantic_hooks if "debug" in hook.lower()}

        has_integrated_hook = bool(debug_hooks) or any("graph-viewer" in hook.lower() for hook in semantic_hooks)
        if not has_integrated_hook:
            self.skipTest("Wave 3 graph viewer/debug hooks not integrated yet")

        self.assertIn("debug", combined.lower())
        self.assertTrue(graph_hooks, "graph UI should expose stable semantic hooks")
        self.assertTrue(debug_hooks, "debug UI should expose stable semantic hooks")
        self.assertIn("/api/graph/data", app_js)
