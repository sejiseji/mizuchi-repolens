# Kuchinawa Reuse Notes

Status: initial inspection, 2026-04-29

## Candidate Sources

Observed Kuchinawa resources under:

- `<KUCHINAWA_ROOT>/runner/file_insight_engine/`
- `<KUCHINAWA_ROOT>/docs/specs/`
- `<KUCHINAWA_ROOT>/tests/test_dashboard*.py`

## Safe Reuse Direction

Prefer copying or adapting standalone logic into Mizuchi modules instead of importing Kuchinawa modules directly.

Likely useful:

- FileInsight dataclass shape ideas from `contracts.py`.
- Directory inventory, deterministic index, and relation graph concepts.
- Evidence normalization patterns from `evidence.py`.
- Summary/role grouping concepts from `summary.py`.
- Dashboard/FileOverview specs and tests as UI behavior references.

## Coupling Risks

Do not directly depend on Kuchinawa policy/artifact behavior until isolated:

- `evidence.py` writes manifests through `effective_policy.artifact_dir()`.
- FileInsight modules are under `runner/`, which may carry runtime assumptions.
- Dashboard-related tests/specs mention CommandCenter and Sheets flows in nearby modules.

## Mizuchi Boundary

Mizuchi adapters should:

- Accept an explicit `ProjectRoot` and `CachePath`.
- Return Mizuchi contracts or plain dictionaries.
- Write only into Mizuchi cache paths when explicitly asked to persist cache artifacts.
- Avoid imports from CommandCenter, Task/Campaign, Codex execution, patch, Sheets, validator, or runtime-loop modules.
- Treat Kuchinawa artifacts as optional compatibility inputs only, never required inputs.

## Wave 2 Worker B Reuse Notes

Inspected but did not import:

- `runner/file_insight_engine/contracts.py`
- `runner/file_insight_engine/inventory.py`
- `runner/file_insight_engine/evidence.py`
- `runner/file_insight_engine/classifier.py`
- `runner/file_domain_map.py`

Adapted into Mizuchi-owned code:

- Stable path-token extraction for inventory payloads, based on the Kuchinawa directory inventory idea but without content digests, artifact writes, policy objects, or target-repo writes.
- Coarse file-domain tags and domain-to-role fallback concepts, reduced to deterministic path/extension checks in `mizuchi.insight.adapters`.
- Evidence placeholder shape inspired by Kuchinawa normalized evidence items: each file now gets source-file, role-hint, and path-token `EvidenceRef` entries.
- Summary-lite shape inspired by FileInsight summary sections: each placeholder has ready text plus identity/classification sections.

Not reused:

- Kuchinawa local LLM role classification, artifact writers, `artifact_dir()`, `PROJECT_ROOT`, policy objects, CommandCenter/Task/Campaign/Codex/Sheets/patch/runtime-loop integrations, or existing artifacts.
