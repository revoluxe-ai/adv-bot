"""Pydantic-модели журнала решений V3 (KeywordDecisionTraceSnapshot)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class TraceStepStatus(StrEnum):
    """Исход фазы executor для одного ключа."""

    APPLY = "APPLY"
    SKIP = "SKIP"
    BLOCK = "BLOCK"
    PASS = "PASS"


class KeywordDecisionTraceStep(BaseModel):
    """Один шаг cascade для ключа: executor → решение → hint-состояние после фазы."""

    order: int
    phase_id: str
    executor_name: str
    status: TraceStepStatus
    decision_ru: str
    reason_ru: str
    state_after: str
    status_hint_after: str
    target_place_after: int | None = None
    processed_at: datetime | None = None


class KeywordDecisionTraceEntry(BaseModel):
    """Полный trace одного operable ключа на тике."""

    keyword_setting_id: int
    keyword_text: str
    nmids: list[int] = Field(default_factory=list[int])
    nmid_display: str = ""

    processing_started: bool = True
    processing_started_at: datetime

    status_hint_before: str
    state_before: str
    status_hint_after: str
    state_after: str

    data_tier: str | None = None

    steps: list[KeywordDecisionTraceStep] = Field(
        default_factory=list[KeywordDecisionTraceStep]
    )

    final_decision_ru: str
    decisive_executor: str | None = None
    decisive_reason_ru: str | None = None
    net_changed: bool = False


class KeywordDecisionTraceSnapshot(BaseModel):
    """Audit последнего NORMAL preamble для operable keywords кампании."""

    tick_started_at: datetime
    processing_started_at: datetime
    tick_finished_at: datetime | None = None
    tick_at: datetime
    adv_id: int
    source: str = "v3_preamble_observer"
    operable_keywords: int
    nmids: list[int] = Field(default_factory=list[int])
    entries: list[KeywordDecisionTraceEntry] = Field(
        default_factory=list[KeywordDecisionTraceEntry]
    )

    def find_by_keyword_setting_id(
        self,
        keyword_setting_id: int,
    ) -> KeywordDecisionTraceEntry | None:
        """Primary lookup по ``keyword_setting_id``."""
        for entry in self.entries:
            if entry.keyword_setting_id == keyword_setting_id:
                return entry
        return None

    def find_by_keyword_text(self, text: str) -> KeywordDecisionTraceEntry | None:
        """Lookup по тексту ключа (case-insensitive, trim)."""
        needle = text.strip().casefold()
        for entry in self.entries:
            if entry.keyword_text.strip().casefold() == needle:
                return entry
        return None
