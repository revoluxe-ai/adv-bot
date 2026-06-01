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
    pay_for_cart: float | None = None,
) -> ModeCandidate:
    pfc = pay_for_cart
    if pfc is None and conv_cart > 0:
        pfc = (1.0 / conv_cart) * bid / 1000.0
    return ModeCandidate(
        mode=mode,
        bid=bid,
        position=position,
        predicted_cpa=cpa,
        predicted_conversion=conv_cart,
        predicted_orders_per_view=conv_cart * 0.247 if conv_cart else None,
        pay_for_cart=pfc,
        is_valid=True,
    )


def _profile_data(**kwargs: object) -> KeywordV3ProfileData:
    defaults = {
        "current_mode": KeywordStrategyMode.MIN_CPA,
        "candidates": {},
        "conv_views_to_cart": 0.0224,
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
    assert "РК 7д корз→заказ" in text
    assert "п|с|к→к|к→з|PFC|CPO" in text
    assert "П — state выше полочной" in text
    assert "CPO = PFC /" in text
    assert "OFF — отключен" in text
    assert "лестница отключена" not in text
    assert "🌟" in text and "M п12|с145" in text
    assert "к→к2.1%" in text
    assert "к→з" in text
    assert "O п8|с210" in text
    assert "Цель режима M" in text
    joined = "\n".join(lines)
    assert (
        joined.index("OFF")
        < joined.index("M п")
        < joined.index("O п")
        < joined.index("C п")
    )


@pytest.mark.unit
def test_profile_shows_rk_cart_to_order_conversion() -> None:
    """Строка РК 7д: доля зак/корз и обратная корз/зак для проверки CPO."""
    data = _profile_data(
        campaign_orders_per_cart_7d=0.247,
        key_orders_7d=5,
        key_carts_7d=20,
        key_orders_per_cart_raw=0.25,
        key_orders_per_cart_smoothed=0.24,
        prior_carts_strength=100,
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 1, 4580.0, 143.32
            ),
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "РК 7д корз→заказ: 24.7%" in text
    assert "0.247 зак/корз" in text
    assert "ключ корз→заказ raw:" in text
    assert "ключ корз→заказ сглаж.:" in text
    assert "prior: 100 корзин" in text
    assert "сглаженная ключевая корз→заказ" in text
    assert "корз/зак" in text


@pytest.mark.unit
def test_profile_stage_conv_from_candidate_not_keyword_aggregate() -> None:
    """к→к в строке M/O/C — ``predicted_conversion`` точки CH, не факт ключа."""
    data = _profile_data(
        conv_views_to_cart=0.0072,
        candidates={
            AggressionTargetMode.MIN_CPA: _valid_candidate(
                AggressionTargetMode.MIN_CPA, 22, 510.0, 402.31, conv_cart=0.009
            ),
            AggressionTargetMode.OPTIMUM: _valid_candidate(
                AggressionTargetMode.OPTIMUM, 1, 20450.0, 16131.92, conv_cart=0.015
            ),
            AggressionTargetMode.MAX_CONVERSION: _valid_candidate(
                AggressionTargetMode.MAX_CONVERSION, 1, 20450.0, 16131.92, conv_cart=0.02
            ),
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "к→к0.9%" in text
    assert "к→к1.5%" in text
    assert "к→к2%" in text
    assert "к→к0.72%" not in text


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
    assert "к→к2.1%" in text
    assert "CTR" not in text
    assert "РК 7д корз→заказ" in text


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
    assert "V2 CPO" in text and "CH матрица" in text
    assert "min bid WB" not in text
    assert "п|с|CPO" not in text
    assert "CPO=" not in text
    assert "OFF —" not in text


@pytest.mark.unit
def test_profile_collapsed_ch_pay_for_order_min_line() -> None:
    """Collapsed CH + pay_for_order: M п0|min|CPO|PFO, O/C нет CH ladder, без maxРК."""
    from app.modules.shop_runner.service_manager.services.auto_updater_v3.dto import (
        AggressionTargetMode,
        ModeCandidate,
    )

    data = KeywordV3ProfileData(
        current_mode=KeywordStrategyMode.MIN_CPA,
        candidates={
            AggressionTargetMode.MIN_CPA: ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                is_valid=True,
                predicted_cpa=382.04,
                position=0,
            ),
            AggressionTargetMode.OPTIMUM: ModeCandidate(
                mode=AggressionTargetMode.OPTIMUM,
                is_valid=False,
                invalid_reason="no_valid_ch_ladder",
            ),
            AggressionTargetMode.MAX_CONVERSION: ModeCandidate(
                mode=AggressionTargetMode.MAX_CONVERSION,
                is_valid=False,
                invalid_reason="no_valid_ch_ladder",
            ),
        },
        keyword_pay_for_order=382.04,
        stage_sources={
            AggressionTargetMode.MIN_CPA: "pay_for_order",
            AggressionTargetMode.OPTIMUM: "none",
            AggressionTargetMode.MAX_CONVERSION: "none",
        },
    )
    text = format_keyword_v3_profile_block(data)
    assert "п0|min|CPO382.04|pay_for_order" in text
    assert "maxРК" not in text
    assert "нет CH ladder" in text


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
                is_valid=True,
                predicted_cpa=367.13,
            ),
        },
        n_state=False,
        no_ch_min_only=True,
        keyword_pay_for_order=367.13,
        diagnostic=KeywordV3DataDiagnostic(
            has_v2_cpo=True,
            has_ch_position_profile=False,
            decision_tier=KeywordV3DecisionTier.NO_CH_MATRIX,
        ),
    )
    text = format_keyword_v3_profile_block(data)
    assert "NO CH (только MIN)" in text
    assert "N-state" not in text
    assert "CPO=" not in text
    assert "(V2)" not in text
    assert "maxРК" not in text
    assert "себест. заказа" in text
    assert "O/C —" not in text
    assert "min bid WB" not in text
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
    assert "M п12|с145|к→к2.1%|к→з" in text
    assert "РК 7д корз→заказ" in text
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
def test_profile_worst_source_simplified_line_shows_max_rk_suffix() -> None:
    """CH + worst, без поз/ставки: упрощённая строка с ``|maxРК``, как полный формат."""
    data = _profile_data(
        diagnostic=KeywordV3DataDiagnostic(
            has_v2_cpo=False,
            has_ch_position_profile=True,
            decision_tier=KeywordV3DecisionTier.NO_CONV,
        ),
        candidates={
            AggressionTargetMode.MIN_CPA: ModeCandidate(
                mode=AggressionTargetMode.MIN_CPA,
                predicted_cpa=814.0,
                is_valid=True,
                position=None,
                bid=None,
            ),
        },
        campaign_worst_costs={AggressionTargetMode.MIN_CPA: 814.0},
        stage_sources={AggressionTargetMode.MIN_CPA: "worst"},
    )
    text = format_keyword_v3_profile_block(data)
    assert "M CPO=814.00|maxРК814" in text
    assert " (max РК)" not in text


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
