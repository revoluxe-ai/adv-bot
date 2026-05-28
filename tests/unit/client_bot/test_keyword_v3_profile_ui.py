"""Тесты блока профиля ключа V3 в Telegram."""

from __future__ import annotations

import pytest

from app.client_bot.user_interface.views.keyword_v3_profile_ui import (
    KeywordV3ProfileData,
    format_keyword_v3_profile_block,
)
from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
    AggressionTargetMode,
    ModeCandidate,
)


def _valid_candidate(mode: AggressionTargetMode, position: int, bid: float, cpa: float) -> ModeCandidate:
    return ModeCandidate(
        mode=mode,
        bid=bid,
        position=position,
        predicted_cpa=cpa,
        is_valid=True,
    )


@pytest.mark.unit
def test_profile_off_first_and_star_on_current() -> None:
    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.MIN_CPA,
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 12, 145.0, 89.5
            ),
            AggressionTargetMode.OPTIMUM: _valid_candidate(
                AggressionTargetMode.OPTIMUM, 8, 210.0, 102.0
            ),
            AggressionTargetMode.MAX_CONVERSION: _valid_candidate(
                AggressionTargetMode.MAX_CONVERSION, 3, 380.0, 145.0
            ),
        },
        raw_bid_positions=None,
        target_positions_by_mode={
            KeywordStrategyMode.MIN_CPA: 12,
            KeywordStrategyMode.OPTIMUM: 8,
            KeywordStrategyMode.MAX_CONVERSION: 3,
        },
    )
    text = format_keyword_v3_profile_block(data)
    lines = [ln for ln in text.strip().split("\n") if ln.strip()]
    assert lines[0].startswith("📊")
    assert "OFF — отключен" in lines[1]
    assert "лестница отключена" not in text
    assert lines[1].startswith("   ")
    assert "🌟" in lines[2] and "MIN_CPA" in lines[2]
    assert "OPTIMUM" in lines[3]
    assert "MAX_CONVERSION" in lines[4]
    joined = "\n".join(lines)
    assert joined.index("OFF") < joined.index("MIN_CPA") < joined.index("OPTIMUM") < joined.index(
        "MAX_CONVERSION"
    )


@pytest.mark.unit
def test_profile_star_on_off() -> None:
    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.OFF,
        candidates={},
        raw_bid_positions=None,
        target_positions_by_mode={},
    )
    text = format_keyword_v3_profile_block(data)
    assert "🌟 o OFF — отключен" in text


@pytest.mark.unit
def test_profile_unavailable_when_none() -> None:
    text = format_keyword_v3_profile_block(None)
    assert "недоступен" in text
