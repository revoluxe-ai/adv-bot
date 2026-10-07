"""Reference-only value types (no authoritative payload duplication)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ApplyEvidenceRef:
    """Apply execution evidence reference (id + optional digest; no receipt body)."""

    apply_evidence_id: str
    digest: str | None = None


@dataclass(frozen=True, slots=True)
class ChangeSetRef:
    """ChangeSet linkage reference."""

    changeset_id: str
    semantic_digest: str


@dataclass(frozen=True, slots=True)
class MetricSpecRef:
    """Versioned metric definition reference for plans and factual results."""

    metric_id: str
    metric_definition_version: str
    source_family: str
    grain: str
    scope: str
    numerator_semantics: str
    denominator_semantics: str | None = None


@dataclass(frozen=True, slots=True)
class SettingsStateRef:
    """Settings history snapshot / state token reference."""

    state_token: str
    snapshot_id: str | None = None


@dataclass(frozen=True, slots=True)
class AttributionFactSetRef:
    """Optional attribution facts bundle reference."""

    attribution_fact_set_id: str
    digest: str | None = None
