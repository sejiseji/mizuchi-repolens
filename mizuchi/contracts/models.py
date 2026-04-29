"""Stable shared data contracts for Mizuchi RepoLens.

Workers may import these models, but contract changes are manager-owned.
The models intentionally avoid assumptions about Kuchinawa runtime state.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Generic, Literal, TypeVar


JsonDict = dict[str, Any]
T = TypeVar("T")


class NodeKind(StrEnum):
    FILE = "file"
    FOLDER = "folder"


class SummaryStatus(StrEnum):
    MISSING = "missing"
    PENDING = "pending"
    READY = "ready"
    ERROR = "error"


class ViewMode(StrEnum):
    ROLE = "role"
    FOLDER = "folder"
    DEPENDENCY = "dependency"
    GIT_CLUSTER = "git_cluster"
    DOMAIN = "domain"


class EdgeKind(StrEnum):
    FOLDER = "folder"
    DEPENDENCY = "dependency"
    CO_CHANGE = "co_change"
    DOMAIN = "domain"
    ISSUE = "issue"


class EdgeDirection(StrEnum):
    DIRECTED = "directed"
    UNDIRECTED = "undirected"


class EdgeRoutingLevel(StrEnum):
    PREVIEW = "preview"
    STANDARD = "standard"
    PRECISE = "precise"


@dataclass(frozen=True)
class ProjectRoot:
    """Opened project identity. The target repository is read-only."""

    path: Path
    display_name: str
    project_hash: str
    is_git_repo: bool
    opened_at: datetime

    def as_json(self) -> JsonDict:
        data = asdict(self)
        data["path"] = str(self.path)
        data["opened_at"] = self.opened_at.isoformat()
        return data


@dataclass(frozen=True)
class CachePath:
    """Standalone cache location outside the opened project root."""

    root: Path
    project_hash: str

    @property
    def project_dir(self) -> Path:
        return self.root / self.project_hash

    def as_json(self) -> JsonDict:
        return {
            "root": str(self.root),
            "project_hash": self.project_hash,
            "project_dir": str(self.project_dir),
        }


@dataclass(frozen=True)
class EvidenceRef:
    file: str
    line: int | None = None
    text: str | None = None
    kind: str | None = None


@dataclass(frozen=True)
class FileNode:
    id: str
    path: str
    folder: str
    language: str | None = None
    role: str = "unknown"
    role_confidence: float = 0.0
    summary_status: SummaryStatus = SummaryStatus.MISSING
    issue_count: int = 0
    degree: int = 0
    port_count: Literal[16, 24] = 16
    last_modified_commit: str | None = None
    kind: NodeKind = NodeKind.FILE


@dataclass(frozen=True)
class FolderNode:
    id: str
    path: str
    parent: str | None = None
    capture_children: bool = True
    collapsed: bool = False
    child_count: int = 0
    visible_child_count: int = 0
    volatile: bool = False
    layout_affects_parent: bool = True
    shape: Literal["rect"] = "rect"
    kind: NodeKind = NodeKind.FOLDER


@dataclass(frozen=True)
class Edge:
    id: str
    source: str
    target: str
    kind: EdgeKind
    direction: EdgeDirection
    certainty: Literal["confirmed", "inferred", "candidate"]
    weight: float = 1.0
    relation_tags: tuple[str, ...] = field(default_factory=tuple)
    evidence_level: str | None = None
    label: str | None = None
    detail_label: str | None = None
    evidence_refs: tuple[EvidenceRef, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GraphData:
    project_hash: str
    generated_at: datetime
    nodes: tuple[FileNode | FolderNode, ...] = field(default_factory=tuple)
    edges: tuple[Edge, ...] = field(default_factory=tuple)
    metadata: JsonDict = field(default_factory=dict)

    def as_json(self) -> JsonDict:
        data = asdict(self)
        data["generated_at"] = self.generated_at.isoformat()
        return data


@dataclass(frozen=True)
class LayoutPosition:
    node_id: str
    x: float
    y: float
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class LayoutManifest:
    project_graph_hash: str
    folder_hash: str | None = None
    dependency_hash: str | None = None
    git_cochange_hash: str | None = None
    role_hash: str | None = None
    domain_probe_hash: str | None = None
    computed_at: datetime | None = None


@dataclass(frozen=True)
class LayoutCache:
    layouts: dict[ViewMode, tuple[LayoutPosition, ...]]
    manifest: LayoutManifest


@dataclass(frozen=True)
class EdgeRoutePoint:
    x: float
    y: float


@dataclass(frozen=True)
class EdgeRoute:
    edge_id: str
    source_port: int
    target_port: int
    points: tuple[EdgeRoutePoint, ...]
    routing_level: EdgeRoutingLevel = EdgeRoutingLevel.PREVIEW


@dataclass(frozen=True)
class EdgeRouteSet:
    routes: tuple[EdgeRoute, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class RenderIndex:
    visible_edges_by_view: dict[ViewMode, tuple[str, ...]] = field(default_factory=dict)
    edge_index_by_relation_tag: dict[str, tuple[str, ...]] = field(default_factory=dict)
    style_tokens_by_encoding: dict[str, JsonDict] = field(default_factory=dict)


@dataclass(frozen=True)
class GitCommitSummary:
    commit_hash: str
    short_hash: str
    date: datetime
    author: str
    message: str
    changed_files_count: int
    selected_file_touched: bool = False


@dataclass(frozen=True)
class GitCommitDetail(GitCommitSummary):
    changed_files: tuple[str, ...] = field(default_factory=tuple)
    body: str = ""


@dataclass(frozen=True)
class DiffResult:
    commit_hash: str
    path: str | None
    diff_text: str
    truncated: bool = False
    max_bytes: int | None = None


@dataclass(frozen=True)
class ApiError:
    code: str
    message: str
    detail: JsonDict | None = None


@dataclass(frozen=True)
class ApiResponse(Generic[T]):
    ok: bool
    data: T | None = None
    error: ApiError | None = None

    @classmethod
    def success(cls, data: T) -> "ApiResponse[T]":
        return cls(ok=True, data=data)

    @classmethod
    def failure(cls, code: str, message: str, detail: JsonDict | None = None) -> "ApiResponse[Any]":
        return cls(ok=False, error=ApiError(code=code, message=message, detail=detail))
