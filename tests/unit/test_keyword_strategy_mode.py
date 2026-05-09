"""Unit tests for KeywordStrategyMode (mapped via SAEnum on KeywordSetting.strategy_mode)."""

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.common_slaves.wildberries.models.models import KeywordSetting


@pytest.mark.unit
def test_keyword_strategy_mode_values() -> None:
    assert KeywordStrategyMode.OFF == 0
    assert KeywordStrategyMode.MIN_CPA == 1
    assert KeywordStrategyMode.OPTIMUM == 2
    assert KeywordStrategyMode.MAX_CONVERSION == 3


@pytest.mark.unit
def test_keyword_setting_strategy_mode_column_defaults() -> None:
    """ORM/DB defaults match KeywordSetting.strategy_mode in models.py."""
    col = KeywordSetting.__table__.c.strategy_mode
    assert col.nullable is False
    assert col.default is not None
    assert col.default.arg == KeywordStrategyMode.MIN_CPA
    assert col.server_default is not None
    assert col.server_default.arg == KeywordStrategyMode.MIN_CPA.name


@pytest.mark.unit
def test_keyword_setting_instantiation_without_explicit_strategy_mode() -> None:
    """Creating KeywordSetting without strategy_mode must not raise."""
    KeywordSetting(text="x", adv_setting_id=1)  # type: ignore[no-untyped-call]
