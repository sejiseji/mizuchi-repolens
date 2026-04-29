"""Standalone FileInsight adapter contracts.

These protocols are deliberately independent of Kuchinawa internals. The
fallback adapter returns lightweight placeholders suitable for quick scans.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from mizuchi.contracts.models import EvidenceRef, SummaryStatus
from mizuchi.project.inventory import detect_language, path_tokens


@dataclass(frozen=True)
class InsightSummary:
    text: str
    status: SummaryStatus = SummaryStatus.READY
    sections: tuple[dict[str, Any], ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RoleInference:
    role: str = "unknown"
    confidence: float = 0.0
    reason: str = ""


@dataclass(frozen=True)
class InsightIssue:
    code: str
    message: str
    severity: str = "info"
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class FileInsightResult:
    path: str
    evidence: tuple[EvidenceRef, ...] = field(default_factory=tuple)
    summary: InsightSummary = field(default_factory=lambda: InsightSummary(text=""))
    role: RoleInference = field(default_factory=RoleInference)
    issues: tuple[InsightIssue, ...] = field(default_factory=tuple)


ROLE_BY_DOMAIN = {
    "ui_presentation": "ui",
    "api_integration": "api",
    "state_management": "state",
    "data_schema": "schema",
    "validation_policy": "validation",
    "runtime_orchestration": "runtime",
    "testing": "test",
    "docs_config": "documentation",
    "asset_resource": "asset",
}

CONFIG_FILENAMES = frozenset(
    {
        ".dockerignore",
        ".editorconfig",
        ".env",
        ".env.example",
        ".env.local",
        ".gitattributes",
        ".gitignore",
        ".npmrc",
        ".pre-commit-config.yaml",
        ".prettierrc",
        ".python-version",
        ".ruff.toml",
        "cargo.toml",
        "composer.json",
        "docker-compose.yml",
        "eslint.config.js",
        "go.mod",
        "go.sum",
        "jest.config.js",
        "makefile",
        "mypy.ini",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pyproject.toml",
        "requirements.txt",
        "setup.cfg",
        "setup.py",
        "tsconfig.json",
        "uv.lock",
        "vite.config.js",
        "webpack.config.js",
        "yarn.lock",
    }
)

ENTRYPOINT_FILENAMES = frozenset(
    {
        "__main__.py",
        "app.py",
        "main.go",
        "main.py",
        "main.rs",
        "server.js",
        "server.ts",
        "wsgi.py",
    }
)

ASSET_SUFFIXES = frozenset(
    {
        ".bmp",
        ".gif",
        ".ico",
        ".jpeg",
        ".jpg",
        ".mp3",
        ".ogg",
        ".otf",
        ".png",
        ".svg",
        ".ttf",
        ".wav",
        ".webp",
        ".woff",
        ".woff2",
    }
)

STYLE_SUFFIXES = frozenset({".css", ".scss", ".sass", ".less"})


class EvidenceProvider(Protocol):
    def evidence_for_file(self, project_root: Path, relative_path: str) -> tuple[EvidenceRef, ...]:
        """Return evidence references for a project-relative file path."""


class SummaryProvider(Protocol):
    def summarize_file(self, project_root: Path, relative_path: str) -> InsightSummary:
        """Return summary metadata for a project-relative file path."""


class RoleProvider(Protocol):
    def infer_role(self, project_root: Path, relative_path: str) -> RoleInference:
        """Return a lightweight role classification."""


class IssueProvider(Protocol):
    def issues_for_file(self, project_root: Path, relative_path: str) -> tuple[InsightIssue, ...]:
        """Return known issues for a project-relative file path."""


class FileInsightAdapter(EvidenceProvider, SummaryProvider, RoleProvider, IssueProvider, Protocol):
    def inspect_file(self, project_root: Path, relative_path: str) -> FileInsightResult:
        """Return all insight facets for a project-relative file path."""


class FallbackFileInsightAdapter:
    """No-dependency FileInsight adapter used until richer analyzers exist."""

    def evidence_for_file(self, project_root: Path, relative_path: str) -> tuple[EvidenceRef, ...]:
        role = self.infer_role(project_root, relative_path)
        refs = [
            EvidenceRef(file=relative_path, kind="source_file", text="project-relative file"),
            EvidenceRef(file=relative_path, kind="role_hint", text=f"{role.role}:{role.reason or 'no strong signal'}"),
        ]
        refs.extend(
            EvidenceRef(file=relative_path, kind="path_token", text=token)
            for token in path_tokens(relative_path, limit=4)
        )
        return tuple(refs)

    def summarize_file(self, project_root: Path, relative_path: str) -> InsightSummary:
        role = self.infer_role(project_root, relative_path)
        path = Path(relative_path)
        language = detect_language(path)
        folder = _display_folder(path)
        role_label = role.role.replace("_", " ")
        language_label = language or _fallback_kind(path)
        text = f"{language_label} {role_label} file in {folder}."
        return InsightSummary(
            text=text,
            sections=(
                {"section_key": "identity", "items": [relative_path]},
                {"section_key": "classification", "items": [role.role, role.reason or "no strong signal"]},
            ),
        )

    def infer_role(self, project_root: Path, relative_path: str) -> RoleInference:
        path = Path(relative_path)
        name = path.name.lower()
        parts = tuple(part.lower() for part in path.parts)
        normalized = relative_path.replace("\\", "/").lower()
        suffix = path.suffix.lower()

        if _is_test_path(name, parts, normalized):
            return RoleInference(role="test", confidence=0.82, reason="test path or filename")
        if name in {"readme", "readme.md", "readme.txt", "license", "license.md", "copying"} or "docs" in parts:
            return RoleInference(role="documentation", confidence=0.78, reason="documentation path or filename")
        if name in CONFIG_FILENAMES or suffix in {".toml", ".ini", ".cfg"}:
            return RoleInference(role="configuration", confidence=0.74, reason="known project configuration file")
        if name in ENTRYPOINT_FILENAMES:
            return RoleInference(role="entrypoint", confidence=0.7, reason="common runtime entrypoint filename")
        if ".github" in parts or "workflows" in parts or name.endswith(".yml") and "ci" in normalized:
            return RoleInference(role="ci", confidence=0.68, reason="CI workflow path")
        if name in {"dockerfile", "containerfile"} or normalized.endswith(("/dockerfile", "/containerfile")):
            return RoleInference(role="container", confidence=0.7, reason="container build filename")
        if suffix in ASSET_SUFFIXES or any(part in {"assets", "images", "icons", "fonts", "media"} for part in parts):
            return RoleInference(role="asset", confidence=0.72, reason="asset extension or resource directory")
        if suffix in STYLE_SUFFIXES:
            return RoleInference(role="style", confidence=0.7, reason="stylesheet extension")
        if suffix in {".json", ".yaml", ".yml"} or any(marker in normalized for marker in ("schema", "migration", "model")):
            return RoleInference(role="schema", confidence=0.58, reason="structured data or schema marker")
        if any(marker in normalized for marker in ("api", "client", "request", "response", "fetch", "http")):
            return RoleInference(role="api", confidence=0.56, reason="API/integration path marker")
        if any(marker in normalized for marker in ("state", "store", "context", "cache", "snapshot")):
            return RoleInference(role="state", confidence=0.56, reason="state/cache path marker")
        if any(marker in normalized for marker in ("runner", "engine", "runtime", "orchestrat")):
            return RoleInference(role="runtime", confidence=0.54, reason="runtime/orchestration path marker")
        if suffix in {".c", ".cc", ".cpp", ".cs", ".go", ".java", ".js", ".jsx", ".kt", ".php", ".py", ".rb", ".rs", ".swift", ".ts", ".tsx"}:
            return RoleInference(role="source", confidence=0.45, reason="source code extension")
        return RoleInference()

    def issues_for_file(self, project_root: Path, relative_path: str) -> tuple[InsightIssue, ...]:
        return ()

    def inspect_file(self, project_root: Path, relative_path: str) -> FileInsightResult:
        return FileInsightResult(
            path=relative_path,
            evidence=self.evidence_for_file(project_root, relative_path),
            summary=self.summarize_file(project_root, relative_path),
            role=self.infer_role(project_root, relative_path),
            issues=self.issues_for_file(project_root, relative_path),
        )


def file_insight_result_to_payload(result: FileInsightResult) -> dict[str, Any]:
    return {
        "path": result.path,
        "evidence": [evidence_ref_to_payload(ref) for ref in result.evidence],
        "summary": {
            "text": result.summary.text,
            "status": result.summary.status.value,
            "sections": list(result.summary.sections),
        },
        "role": {
            "role": result.role.role,
            "confidence": result.role.confidence,
            "reason": result.role.reason,
        },
        "issues": [
            {
                "code": issue.code,
                "message": issue.message,
                "severity": issue.severity,
                "evidence": [evidence_ref_to_payload(ref) for ref in issue.evidence],
            }
            for issue in result.issues
        ],
    }


def evidence_ref_to_payload(ref: EvidenceRef) -> dict[str, Any]:
    return {
        "file": ref.file,
        "line": ref.line,
        "text": ref.text,
        "kind": ref.kind,
    }


def classify_file_domain_tag(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/").lower().strip()
    suffix = Path(normalized).suffix.lower()
    if _is_test_path(Path(normalized).name, tuple(Path(normalized).parts), normalized):
        return "testing"
    if normalized.startswith("docs/") or suffix in {".md", ".rst", ".txt", ".toml", ".ini", ".cfg"}:
        return "docs_config"
    if suffix in ASSET_SUFFIXES or any(marker in normalized for marker in ("assets/", "/assets/", "icons/", "images/", "fonts/")):
        return "asset_resource"
    if suffix in {".json", ".yaml", ".yml"} or any(marker in normalized for marker in ("schema", "migration", "model")):
        return "data_schema"
    if any(marker in normalized for marker in ("validator", "validation")):
        return "validation_policy"
    if any(marker in normalized for marker in ("api", "http", "client", "request", "response", "fetch")):
        return "api_integration"
    if any(marker in normalized for marker in ("state", "store", "context", "snapshot", "cache")):
        return "state_management"
    if any(marker in normalized for marker in ("runner", "engine", "runtime", "orchestrat")):
        return "runtime_orchestration"
    if suffix in STYLE_SUFFIXES or any(marker in normalized for marker in ("component", "view", "page", "screen")):
        return "ui_presentation"
    return "unknown"


def domain_fallback_role(domain_tag: str) -> str:
    return ROLE_BY_DOMAIN.get(domain_tag, "unknown")


def _is_test_path(name: str, parts: tuple[str, ...], normalized: str) -> bool:
    return (
        name.startswith("test_")
        or name.endswith("_test.py")
        or name.endswith(".test.ts")
        or name.endswith(".spec.ts")
        or name.endswith(".test.tsx")
        or name.endswith(".spec.tsx")
        or "tests" in parts
        or "__tests__" in parts
        or normalized.startswith("test/")
    )


def _display_folder(path: Path) -> str:
    parent = path.parent.as_posix()
    return "project root" if parent == "." else parent


def _fallback_kind(path: Path) -> str:
    suffix = path.suffix.lower().lstrip(".")
    return f"{suffix.upper()} file" if suffix else "Project"
