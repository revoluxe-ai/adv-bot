"""Модели настроек и состояния управления ставкой полок Auto-РК."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.utils.db.base import Base


class AutoShelfBidControlSettings(Base):
    """Параметры управления ставкой для одного nmid."""

    __tablename__ = "auto_shelf_bid_control_settings"
    __table_args__ = (
        CheckConstraint("max_bid_minor > 0", name="ck_asbcs_max_bid_minor_positive"),
        CheckConstraint(
            "min_bid_distance_minor > 0",
            name="ck_asbcs_min_bid_distance_positive",
        ),
        CheckConstraint(
            "target_test_impressions > 0",
            name="ck_asbcs_target_test_impressions_positive",
        ),
        CheckConstraint(
            "target_test_observation_minutes >= 60",
            name="ck_asbcs_target_test_observation_minutes_min_60",
        ),
        CheckConstraint(
            "test_share > 0 AND test_share <= 0.49",
            name="ck_asbcs_test_share_range",
        ),
        CheckConstraint(
            "retest_interval_days >= 1",
            name="ck_asbcs_retest_interval_days_min_1",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nmid: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    max_bid_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="RUB", nullable=False)
    min_bid_distance_minor: Mapped[int] = mapped_column(
        BigInteger,
        default=1,
        nullable=False,
        comment=(
            "Минимальное расстояние между тестируемыми ставками "
            "(identity units, как bid_minor в AutoShelfBidSetter)."
        ),
    )
    target_test_impressions: Mapped[int] = mapped_column(
        Integer,
        default=500,
        nullable=False,
    )
    target_test_observation_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=True,
        server_default=text('60')
    )
    test_share: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)
    retest_interval_days: Mapped[int] = mapped_column(
        Integer,
        default=7,
        nullable=False,
        server_default=text("7"),
        comment=(
            "Календарный интервал суток до clear our-block shelf-exhausted "
            "(product default 7; INC-AUTO-SHELF-PAUSE-01)."
        ),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @validates(
        "max_bid_minor",
        "min_bid_distance_minor",
        "target_test_impressions",
    )
    def _validate_positive_int(self, key: str, value: int) -> int:
        """Гарантировать положительные значения numeric-настроек."""
        if int(value) <= 0:
            raise ValueError(f"{key} must be positive")
        return int(value)

    @validates("target_test_observation_minutes")
    def _validate_target_test_observation_minutes(self, _: str, value: int) -> int:
        """Минимальная длительность теста — один час."""
        casted = int(value)
        if casted < 60:
            raise ValueError("target_test_observation_minutes must be >= 60")
        return casted

    @validates("test_share")
    def _validate_test_share(self, _: str, value: float) -> float:
        """Ограничить долю теста диапазоном (0, 0.49]."""
        casted = float(value)
        if casted <= 0 or casted > 0.49:
            raise ValueError("test_share must satisfy 0 < test_share <= 0.49")
        return casted

    @validates("retest_interval_days")
    def _validate_retest_interval_days(self, _: str, value: int) -> int:
        """Интервал перетеста — не меньше одних суток."""
        casted = int(value)
        if casted < 1:
            raise ValueError("retest_interval_days must be >= 1")
        return casted


class AutoShelfBidControlState(Base):
    """Текущее состояние цикла управления ставкой для одного nmid."""

    __tablename__ = "auto_shelf_bid_control_state"
    __table_args__ = (
        CheckConstraint(
            "current_mode IN ('main', 'test')",
            name="ck_asbcs_state_current_mode_allowed",
        ),
        CheckConstraint(
            "shelf_exhausted_resolve_cpo_kind IS NULL OR "
            "shelf_exhausted_resolve_cpo_kind IN ('target', 'max')",
            name="ck_asbcs_state_shelf_exhausted_resolve_cpo_kind",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nmid: Mapped[int] = mapped_column(BigInteger, nullable=False, unique=True, index=True)
    current_mode: Mapped[str] = mapped_column(String(16), default="test", nullable=False)
    current_main_bid_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    current_test_bid_minor: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String, default="RUB", nullable=False)
    current_cycle_started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    previous_cycle_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    main_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    test_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # INC-AUTO-SHELF-PAUSE-01: canonical our-block / epoch / recorded resolve CPO.
    shelf_exhausted_pause_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment="Our-block: shelf-exhausted pause SoT (PG canonical).",
    )
    shelf_exhausted_paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    shelf_exhausted_due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Календарный due clear our-block.",
    )
    shelf_exhausted_epoch_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Старт эпохи покрытия; пишется при реальном Auto start.",
    )
    shelf_exhausted_resolve_cpo_kind: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="target|max — какой resolve CPO зафиксировали при latch.",
    )
    shelf_exhausted_resolve_cpo_value: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    shelf_exhausted_notify_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Дедуп paid notify при enter pause.",
    )
    shelf_exhausted_epoch_pending: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        server_default=text("false"),
        comment=(
            "True после clear our-block: следующая реальная Auto start "
            "открывает новую эпоху покрытия."
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    @validates("current_mode")
    def _validate_mode(self, _: str, value: str) -> str:
        """Допускать только main/test для mode-контракта."""
        if value not in {"main", "test"}:
            raise ValueError("current_mode must be 'main' or 'test'")
        return value

    @validates("shelf_exhausted_resolve_cpo_kind")
    def _validate_resolve_cpo_kind(self, _: str, value: str | None) -> str | None:
        """Допускать только target|max|None для recorded resolve kind."""
        if value is None:
            return None
        if value not in {"target", "max"}:
            raise ValueError("shelf_exhausted_resolve_cpo_kind must be 'target' or 'max'")
        return value
