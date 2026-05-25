"""Модели настроек и состояния управления ставкой полок Auto-РК."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Float, Integer, String, func
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
            "test_share > 0 AND test_share <= 0.49",
            name="ck_asbcs_test_share_range",
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
    test_share: Mapped[float] = mapped_column(Float, default=0.1, nullable=False)

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

    @validates("test_share")
    def _validate_test_share(self, _: str, value: float) -> float:
        """Ограничить долю теста диапазоном (0, 0.49]."""
        casted = float(value)
        if casted <= 0 or casted > 0.49:
            raise ValueError("test_share must satisfy 0 < test_share <= 0.49")
        return casted


class AutoShelfBidControlState(Base):
    """Текущее состояние цикла управления ставкой для одного nmid."""

    __tablename__ = "auto_shelf_bid_control_state"
    __table_args__ = (
        CheckConstraint(
            "current_mode IN ('main', 'test')",
            name="ck_asbcs_state_current_mode_allowed",
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

