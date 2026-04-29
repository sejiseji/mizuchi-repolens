"""Edge semantic helpers for RepoLens graph payloads."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, cast

from mizuchi.contracts.models import EdgeDirection, EdgeKind, EvidenceRef


CERTAINTY_LEVELS = frozenset({"confirmed", "inferred", "candidate"})
Certainty = Literal["confirmed", "inferred", "candidate"]


def normalize_certainty(certainty: str | None, *, default: Certainty = "candidate") -> Certainty:
    """Return a contract-compatible certainty label."""

    value = (certainty or default).strip().lower().replace("-", "_")
    if value not in CERTAINTY_LEVELS:
        return default
    return cast(Certainty, value)


def direction_for_kind(kind: EdgeKind) -> EdgeDirection:
    """Return the default direction semantics for a relation kind."""

    if kind is EdgeKind.CO_CHANGE:
        return EdgeDirection.UNDIRECTED
    return EdgeDirection.DIRECTED


def relation_tags_for_kind(kind: EdgeKind, *extra_tags: str | None) -> tuple[str, ...]:
    """Build stable relation tags, de-duplicating while preserving order."""

    tags = [kind.value]
    tags.extend(tag for tag in extra_tags if tag)
    return normalize_relation_tags(tags)


def normalize_relation_tags(tags: Iterable[str | None]) -> tuple[str, ...]:
    seen: set[str] = set()
    normalized: list[str] = []
    for tag in tags:
        if not tag:
            continue
        value = tag.strip().lower().replace("-", "_").replace(" ", "_")
        if value and value not in seen:
            seen.add(value)
            normalized.append(value)
    return tuple(normalized)


def clamp_weight(weight: float | int | None, *, minimum: float = 0.1, maximum: float = 100.0) -> float:
    """Clamp edge weight to a positive render-friendly range."""

    if weight is None:
        return 1.0
    value = float(weight)
    return min(max(value, minimum), maximum)


def evidence_level_for_refs(refs: Iterable[EvidenceRef]) -> str | None:
    """Describe how strong edge evidence is based on attached source refs."""

    refs_tuple = tuple(refs)
    if not refs_tuple:
        return None
    if any(ref.line is not None for ref in refs_tuple):
        return "line_refs"
    return "file_refs"
