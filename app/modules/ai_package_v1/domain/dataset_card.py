"""Карточка датасета: четыре независимых измерения полноты и provenance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.modules.ai_package_v1.domain.coverage_rules import (
    assert_card_fail_closed,
    validate_independent_dimensions,
)
from app.modules.ai_package_v1.domain.enums import (
    CollectionOutcome,
    Coverage,
    DatasetId,
    FreshnessStatus,
    PrimarySource,
    ReasonCode,
)
from app.modules.ai_package_v1.domain.export_period import ExportPeriod


class Provenance(BaseModel):
    """Происхождение и зерно датасета (без подмены primary_source)."""

    primary_source: PrimarySource
    grain: str
    notes: str | None = None


class DatasetCard(BaseModel):
    """
    Метаданные одного датасета в manifest.

    ``collection_outcome``, ``coverage``, ``reason_codes`` и ``freshness``
    задаются явно и не выводятся друг из друга автоматически.
    """

    dataset_id: DatasetId
    provenance: Provenance
    period: ExportPeriod
    collection_outcome: CollectionOutcome
    coverage: Coverage
    reason_codes: list[ReasonCode] = Field(default_factory=list)
    freshness: FreshnessStatus
    row_file: str | None = None
    row_count: int | None = None

    @field_validator("reason_codes", mode="before")
    @classmethod
    def _coerce_reason_codes(cls, value: Any) -> list[ReasonCode]:
        if value is None:
            return []
        return [ReasonCode(v) if not isinstance(v, ReasonCode) else v for v in value]

    def validate_semantics(self) -> None:
        """Проверяет fail-closed и независимость измерений (raises ValueError)."""
        validate_independent_dimensions(
            self.collection_outcome,
            self.coverage,
            self.reason_codes,
            self.freshness,
        )
        assert_card_fail_closed(self.collection_outcome, self.coverage)

    def to_manifest_dict(self) -> dict[str, Any]:
        """Сериализуемое представление для manifest (стабильные ключи)."""
        self.validate_semantics()
        return {
            "dataset_id": str(self.dataset_id),
            "provenance": {
                "primary_source": str(self.provenance.primary_source),
                "grain": self.provenance.grain,
                "notes": self.provenance.notes,
            },
            "period": self.period.to_manifest_dict(),
            "collection_outcome": str(self.collection_outcome),
            "coverage": str(self.coverage),
            "reason_codes": [str(c) for c in self.reason_codes],
            "freshness": str(self.freshness),
            "row_file": self.row_file,
            "row_count": self.row_count,
        }
