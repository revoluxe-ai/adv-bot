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
from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
    KeywordV3DecisionTier,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
    KeywordV3DataDiagnostic,
)


def _valid_candidate(
    mode: AggressionTargetMode,
    position: int,
    bid: float,
    cpa: float,
    *,
    conv_cart: float = 0.021,
) -> ModeCandidate:
    return ModeCandidate(
        mode=mode,
        bid=bid,
        position=position,
        predicted_cpa=cpa,
        predicted_conversion=conv_cart,
        is_valid=True,
    )


def _profile_data(**kwargs: object) -> KeywordV3ProfileData:
    defaults = {
        "current_mode": KeywordStrategyMode.MIN_CPA,
        "candidates": {},
        "keyword_ctr": 0.0094,
        "conv_views_to_orders": 0.01,
    }
    defaults.update(kwargs)
    return KeywordV3ProfileData(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
def test_profile_off_first_and_star_on_current() -> None:
    data = _profile_data(
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
    assert "п|с|CTR|CPO" in lines[1]
    assert "к→з 1%" in lines[2]
    assert "conv ключа" in lines[2]
    assert "OFF — отключен" in lines[3]
    assert "лестница отключена" not in text
    assert "🌟" in lines[4] and "M п12|с145" in lines[4]
    assert "CTR0.94%" in lines[4]
    assert "CPO89.50" in lines[4]
    assert lines[4].endswith("CPO89.50")
    assert "кк" not in text
    assert "к→з" not in lines[4]
    assert "O п8|с210" in lines[5]
    joined = "\n".join(lines)
    assert (
        joined.index("OFF")
        < joined.index("M п")
        < joined.index("O п")
        < joined.index("C п")
    )


@pytest.mark.unit
def test_profile_star_on_off() -> None:
    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.OFF,
        candidates={},
    )
    text = format_keyword_v3_profile_block(data)
    assert "🌟 o OFF — отключен" in text
    assert "п|с|CPO" not in text


@pytest.mark.unit
def test_profile_unavailable_when_none() -> None:
    text = format_keyword_v3_profile_block(None)
    assert "недоступен" in text


@pytest.mark.unit
def test_profile_invalid_candidate_shows_reason() -> None:
    data = _profile_data(
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
    assert "🌟" in text and "O п5|с200" in text
    assert "CTR0.94%" in text
    assert "к→з 1%" in text


@pytest.mark.unit
def test_profile_n_state_when_no_v2_cpo_and_no_ch() -> None:
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
            has_v2_cpo=False,
            has_ch_position_profile=False,
        ),
    )
    text = format_keyword_v3_profile_block(data)
    assert "N-state" in text
    assert "N-state bootstrap" in text
    assert "V2 CPO" in text and "CH матрица" in text
    assert "min bid WB" in text
    assert "п|с|CPO" not in text


@pytest.mark.unit
def test_profile_no_ch_min_only_not_n_state() -> None:
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.no_data_activation import (
        KeywordV3DataDiagnostic,
    )
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_v3_decision_data import (
        KeywordV3DecisionTier,
    )

    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.OFF,
        candidates={
            AggressionTargetMode.MIN_CPA: ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                is_valid=False,
                invalid_reason="no_position_profile",
            ),
        },
        n_state=False,
        no_ch_min_only=True,
        v2_pay_for_order=367.13,
        diagnostic=KeywordV3DataDiagnostic(
            has_v2_cpo=True,
            has_ch_position_profile=False,
            decision_tier=KeywordV3DecisionTier.NO_CH_MATRIX,
        ),
    )
    text = format_keyword_v3_profile_block(data)
    assert "NO CH (только MIN)" in text
    assert "N-state" not in text
    assert "CPO=367.13 (V2)" in text
    assert "NO CH bootstrap" in text
    assert "нет матрицы CH" in text


@pytest.mark.unit
def test_profile_legacy_markdown_not_v2_escapes() -> None:
    """ParseMode.MARKDOWN: без \\( \\) \\| \\. из MarkdownV2."""
    data = _profile_data(
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
    assert "M п12|с145|CTR0.94%|CPO89.50" in text
    assert "цель" not in text
    assert "*Профиль ключа (V3):*" in text
    assert "имп. max CPO" not in text
    assert "имп. conv" not in text


@pytest.mark.unit
def test_profile_full_tier_no_imputed_header() -> None:
    """FULL: своя conv + CH — без заголовка про импутацию."""
    diag = KeywordV3DataDiagnostic(
        has_v2_cpo=True,
        has_ch_position_profile=True,
        decision_tier=KeywordV3DecisionTier.FULL,
        imputed_conv=False,
    )
    data = _profile_data(
        diagnostic=diag,
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 1, 100.0, 50.0
            ),
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert text.startswith("📊 *Профиль ключа (V3):*\n")
    assert "имп." not in text.split("\n")[0]


@pytest.mark.unit
def test_profile_full_tier_hides_max_rk_when_own_profile() -> None:
    """FULL + source=profile: без |maxРК, даже если worst_costs переданы."""
    data = _profile_data(
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 21, 510.0, 253.84
            ),
            AggressionTargetMode.OPTIMUM: _valid_candidate(
                AggressionTargetMode.OPTIMUM, 1, 12095.0, 6020.02
            ),
            AggressionTargetMode.MAX_CONVERSION: _valid_candidate(
                AggressionTargetMode.MAX_CONVERSION, 1, 12095.0, 6020.02
            ),
        },
        campaign_worst_costs={
            AggressionTargetMode.MIN_CPA: 814.0,
            AggressionTargetMode.OPTIMUM: 23906.0,
            AggressionTargetMode.MAX_CONVERSION: 23906.0,
        },
        stage_sources={
            AggressionTargetMode.MIN_CPA: "profile",
            AggressionTargetMode.OPTIMUM: "profile",
            AggressionTargetMode.MAX_CONVERSION: "profile",
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "maxРК" not in text
    assert "CPO253.84" in text
    assert "(проф)" not in text


@pytest.mark.unit
def test_profile_worst_source_shows_max_rk_suffix() -> None:
    """NO_CONV / worst: CPO из РК + суффикс |maxРК."""
    data = _profile_data(
        diagnostic=KeywordV3DataDiagnostic(
            has_v2_cpo=False,
            has_ch_position_profile=True,
            decision_tier=KeywordV3DecisionTier.NO_CONV,
        ),
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 1, 100.0, 814.0
            ),
        },
        campaign_worst_costs={AggressionTargetMode.MIN_CPA: 814.0},
        stage_sources={AggressionTargetMode.MIN_CPA: "worst"},
    )
    text = format_keyword_v3_profile_block(data)
    assert "|maxРК814" in text
    assert "maxРК — max CPO" in text


@pytest.mark.unit
def test_profile_no_conv_tier_shows_max_rk_header() -> None:
    """NO_CONV + CH: заголовок про max CPO по РК, не про имп. conv."""
    diag = KeywordV3DataDiagnostic(
        has_v2_cpo=False,
        has_ch_position_profile=True,
        decision_tier=KeywordV3DecisionTier.NO_CONV,
        imputed_conv=False,
    )
    data = _profile_data(
        diagnostic=diag,
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 1, 100.0, 50.0
            ),
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "max CPO по РК (нет conv)" in text
    assert "имп. conv" not in text.split("\n")[0]
