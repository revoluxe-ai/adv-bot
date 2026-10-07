"""Reference-only value types (no authoritative payload duplication)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ApplyEvidenceRef:
    """Apply execution evidence reference (opaque id; no receipt body)."""

    apply_evidence_id: str
    evidence_digest: str | None = None
    authority_kind: str = "APPLY_AUTHORITY_V1"


@dataclass(frozen=True, slots=True)
class ChangeSetRef:
    """ChangeSet linkage reference."""

    changeset_id: str
    semantic_digest: str


@dataclass(frozen=True, slots=True)
class MetricAnalysisWindowRef:
    """Window/cutoff refs attached to a metric spec (not metric collection)."""

    analysis_window_label: str | None = None
    evaluation_cutoff: datetime | None = None
    source_complete_through: datetime | None = None


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
    coverage_requirements: tuple[str, ...] = ()
    analysis_window: MetricAnalysisWindowRef | None = None


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
