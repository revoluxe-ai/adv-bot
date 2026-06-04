"""Pydantic-модели post-hoc audit изменений ключей V3."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class V3KeywordStepRecord(BaseModel):
    """Один шаг смены режима ключа с атрибуцией executor."""

    executor_name: str
    from_mode: str
    to_mode: str
    action: str  # UP | DOWN | FORCE_OFF | NOOP


class V3KeywordChangeEntry(BaseModel):
    """Изменённый ключ: netto и пошаговая цепочка."""

    keyword_setting_id: int
    keyword_text: str
    stored_mode: str
    current_mode: str
    mode_chain: str = ""
    executor_short_labels: str = ""
    steps: list[V3KeywordStepRecord] = Field(default_factory=list)
    target_place_steps: list[str] = Field(default_factory=list)

    model_config = {"extra": "forbid"}


class V3ExecutorPhaseBreakdown(BaseModel):
    """Агрегат действий одного executor (мапится на phase_id отчёта)."""

    phase_id: str
    executor_name: str
    title_ru: str = ""
    planned: int = 0
    up: int = 0
    down: int = 0
    force_off: int = 0
    rebalance: int = 0
    keywords_touched: int = 0

    model_config = {"extra": "forbid"}


class V3KeywordChangesSnapshot(BaseModel):
    """Полный audit изменений ключей за один V3-тик."""

    tick_at: datetime
    adv_id: int
    source: str = "keyword_dto"
    changed_keywords: int = 0
    net_up: int = 0
    net_down: int = 0
    net_force_off: int = 0
    aggression_score_after: int = 0
    by_phase: list[V3ExecutorPhaseBreakdown] = Field(default_factory=list)
    keyword_entries: list[V3KeywordChangeEntry] = Field(default_factory=list)

    model_config = {"extra": "forbid"}
