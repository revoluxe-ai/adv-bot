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
    )
    text = format_keyword_v3_profile_block(data)
    lines = [ln for ln in text.strip().split("\n") if ln.strip()]
    assert lines[0].startswith("📊")
    assert "OFF — отключен" in lines[1]
    assert "лестница отключена" not in text
    assert lines[1].startswith("   ")
    assert "🌟" in lines[2] and "M — поз. 12" in lines[2]
    assert "O — поз. 8" in lines[3]
    assert "C — поз. 3" in lines[4]
    joined = "\n".join(lines)
    assert (
        joined.index("OFF")
        < joined.index("M —")
        < joined.index("O —")
        < joined.index("C —")
    )


@pytest.mark.unit
def test_profile_star_on_off() -> None:
    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.OFF,
        candidates={},
    )
    text = format_keyword_v3_profile_block(data)
    assert "🌟 o OFF — отключен" in text


@pytest.mark.unit
def test_profile_unavailable_when_none() -> None:
    text = format_keyword_v3_profile_block(None)
    assert "недоступен" in text


@pytest.mark.unit
def test_profile_invalid_candidate_shows_reason() -> None:
    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.OPTIMUM,
        candidates={
            AggressionTargetMode.MIN_CPA: ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                is_valid=False,
                invalid_reason="no_keyword_conv_views_to_orders",
            ),
            AggressionTargetMode.OPTIMUM: _valid_candidate(
                AggressionTargetMode.OPTIMUM, 5, 200.0, 90.0
            ),
            AggressionTargetMode.MAX_CONVERSION: ModeCandidate(
                mode=AggressionTargetMode.MAX_CONVERSION,
                is_valid=False,
                invalid_reason="no_conversion_points",
            ),
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "нет conv показ→заказ" in text
    assert "нет конверсий" in text
    assert "🌟" in text and "O — поз. 5" in text


@pytest.mark.unit
def test_profile_n_state_when_no_ch_matrix() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        KeywordV3DataDiagnostic,
    )

    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.MIN_CPA,
        candidates={
            AggressionTargetMode.MIN_CPA: ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                is_valid=False,
                invalid_reason="no_position_profile",
            ),
        },
        n_state=True,
        diagnostic=KeywordV3DataDiagnostic(
            has_v2_cpo=True,
            has_ch_position_profile=False,
        ),
    )
    text = format_keyword_v3_profile_block(data)
    assert "N-state" in text
    assert "V2 CPO" in text and "CH матрица" in text
    assert "нет матрицы CH" in text
    assert "min bid WB" in text
    assert "M + target 0" in text
    assert "\\_" not in text
    assert "_Данные:" not in text
    assert "_Нет:" not in text


@pytest.mark.unit
def test_profile_legacy_markdown_not_v2_escapes() -> None:
    """ParseMode.MARKDOWN: без \\( \\) \\| \\. из MarkdownV2."""
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
    )
    text = format_keyword_v3_profile_block(data)
    assert "\\(" not in text
    assert "\\)" not in text
    assert "\\|" not in text
    assert "поз\\. " not in text
    assert "поз. 12 | CPM" in text
    assert "цель" not in text
    assert "*Профиль ключа (V3):*" in text
