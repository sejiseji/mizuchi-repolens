"""FileInsight adapter interfaces and fallback implementation."""

from mizuchi.insight.adapters import (
    EvidenceProvider,
    FallbackFileInsightAdapter,
    FileInsightAdapter,
    FileInsightResult,
    InsightIssue,
    InsightSummary,
    IssueProvider,
    RoleInference,
    RoleProvider,
    SummaryProvider,
    classify_file_domain_tag,
    domain_fallback_role,
    evidence_ref_to_payload,
    file_insight_result_to_payload,
)
from mizuchi.insight.artifacts import CacheInsightArtifactStore, InsightArtifactRef, InsightArtifactStore

__all__ = [
    "EvidenceProvider",
    "CacheInsightArtifactStore",
    "FallbackFileInsightAdapter",
    "FileInsightAdapter",
    "FileInsightResult",
    "InsightArtifactRef",
    "InsightArtifactStore",
    "InsightIssue",
    "InsightSummary",
    "IssueProvider",
    "RoleInference",
    "RoleProvider",
    "SummaryProvider",
    "classify_file_domain_tag",
    "domain_fallback_role",
    "evidence_ref_to_payload",
    "file_insight_result_to_payload",
]
