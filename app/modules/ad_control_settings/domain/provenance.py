"""Provenance effective configured policy."""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlScope,
    EffectiveSourceKind,
)


@dataclass(frozen=True, slots=True)
class ProvenanceEntry:
    """Источник одного effective configured значения feature."""

    feature_id: AdControlFeatureId
    source_kind: EffectiveSourceKind
    source_scope: AdControlScope
    schema_version: int
