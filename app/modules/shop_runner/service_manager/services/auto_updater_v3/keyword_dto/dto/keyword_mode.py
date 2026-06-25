"""Режимы команд ``NextState`` (strategy + validate-команды)."""

from __future__ import annotations

from enum import Enum

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


class KeywordMode(str, Enum):
    """Команда смены режима; маппится в ``KeywordStrategyMode`` внутри ``KeywordDTO``."""

    OFF = "off"
    MIN_CPA = "min_cpa"
    OPTIMUM = "optimum"
    MAX_CONVERSION = "max_conversion"
    NOT_FULL_ACTIVATE = "not_full_activate"

    def to_strategy_mode(self) -> KeywordStrategyMode:
        """Strategy для history/ledger; ``NOT_FULL_ACTIVATE`` → ``MIN_CPA``."""
        if self is KeywordMode.OFF:
            return KeywordStrategyMode.OFF
        if self is KeywordMode.MIN_CPA:
            return KeywordStrategyMode.MIN_CPA
        if self is KeywordMode.OPTIMUM:
            return KeywordStrategyMode.OPTIMUM
        if self is KeywordMode.MAX_CONVERSION:
            return KeywordStrategyMode.MAX_CONVERSION
        if self is KeywordMode.NOT_FULL_ACTIVATE:
            return KeywordStrategyMode.MIN_CPA
        raise ValueError(f"Unknown KeywordMode: {self!r}")

    @classmethod
    def from_strategy_mode(cls, mode: KeywordStrategyMode) -> KeywordMode:
        """Обратный маппинг strategy → команда (без validate-команд)."""
        if mode == KeywordStrategyMode.OFF:
            return cls.OFF
        if mode == KeywordStrategyMode.MIN_CPA:
            return cls.MIN_CPA
        if mode == KeywordStrategyMode.OPTIMUM:
            return cls.OPTIMUM
        if mode == KeywordStrategyMode.MAX_CONVERSION:
            return cls.MAX_CONVERSION
        raise ValueError(f"Unknown KeywordStrategyMode: {mode!r}")
