"""PBH-002: Owner A_PRIME — PFO recovery within confirmed set MUST restore ON.

Owner policy (gates/OWNER_A_B_C_DECISION.json, choice A_PRIME):
- confirmed-set membership frozen after keyword confirm;
- SAFETY_OFF when PFO > max CPO Allowed;
- AUTO_ON when PFO recovers within confirmed set Allowed;
- views permanent OFF latch during WARM_UP lean-disallowed (separate).

Behavioral coverage:
- setup PASS after PFO latch writes return-ON (session.execute);
- ACTIVE hold tick awaits ``apply_ab_hold_pfo_recovery_ons`` with recovered ids.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_hold,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_apply import (
    apply_ab_hold_setup_mutations,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.setup_decision import (
    AbHoldSetupAction,
    classify_ab_hold_setup_keyword,
)

_SETUP_APPLY = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.setup_apply"
)
_PIPELINES = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.pipelines"
)


def _recovered_pass_keyword(
    *,
    ks_id: int = 101,
    text: str = "confirmed-kw",
    views: int = 200,
    pfo: float = 80.0,
) -> SimpleNamespace:
    """Ключ внутри confirmed set: ранее OFF (PFO latch), сейчас PFO recovered (PASS)."""
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        text=text,
        views=views,
        pay_for_order=pfo,
        position=12.0,
        strategy_mode=KeywordStrategyMode.OFF,
        hard_status=1,
    )


def _stmt_sets_non_off_strategy(stmt: Any) -> bool:
    """True, если Update пишет strategy_mode отличный от OFF (return-ON)."""
    values = getattr(stmt, "_values", None) or {}
    for key, value in values.items():
        key_name = str(getattr(key, "key", None) or getattr(key, "name", None) or key)
        if "strategy_mode" not in key_name:
            continue
        raw = getattr(value, "value", value)
        try:
            if int(raw) != int(KeywordStrategyMode.OFF):
                return True
        except (TypeError, ValueError):
            if raw is not KeywordStrategyMode.OFF and str(raw) not in {
                "0",
                "OFF",
                "KeywordStrategyMode.OFF",
            }:
                return True
    return False


def _has_return_on_write(execute_calls: list[Any]) -> bool:
    """Есть ли session.execute с return-ON (non-OFF strategy_mode)."""
    for call in execute_calls:
        if not call.args:
            continue
        if _stmt_sets_non_off_strategy(call.args[0]):
            return True
    return False


@pytest.mark.unit
def test_pbh002_classifier_pass_when_pfo_recovers() -> None:
    """Предусловие A_PRIME: recovered PFO + views >= 100 -> PASS (не FAIL_OFF)."""
    action = classify_ab_hold_setup_keyword(
        pay_for_order=80.0,
        views=200,
        max_pay_for_order=100.0,
    )
    assert action == AbHoldSetupAction.PASS_FIX_TARGET


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh002_a_prime_setup_pass_restores_on_after_pfo_recovery() -> None:
    """A_PRIME: epoch setup PASS after PFO latch MUST write return-ON.

    Scenario: keyword already OFF from prior FAIL->OFF (Allowed), then rolling
    PFO recovers within confirmed set -> classify PASS -> MUST restore operable
    strategy_mode (not stay latched OFF forever).
    """
    kw = _recovered_pass_keyword()
    assert (
        classify_ab_hold_setup_keyword(
            pay_for_order=kw.pay_for_order,
            views=int(kw.views),
            max_pay_for_order=100.0,
        )
        == AbHoldSetupAction.PASS_FIX_TARGET
    )

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
    mock_cm.__aexit__ = AsyncMock(return_value=None)

    with patch(f"{_SETUP_APPLY}.sm", return_value=mock_cm):
        pass_n, fail_n = await apply_ab_hold_setup_mutations(
            adv_id=10,
            adv_setting_id=20,
            keywords=[kw],  # type: ignore[arg-type]
            max_pay_for_order=100.0,
            allowed_phrases_snapshot=[kw.text],
            epoch_managed=True,
        )

    assert pass_n == 1
    assert fail_n == 0
    assert _has_return_on_write(mock_session.execute.call_args_list), (
        "Owner A_PRIME: AUTO_ON_WHEN_PFO_RECOVERS_WITHIN_CONFIRMED_SET — "
        "apply_ab_hold_setup_mutations(epoch_managed=True) MUST restore "
        "strategy_mode away from OFF for PASS keywords previously latched OFF"
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh002_a_prime_hold_tick_restores_on_when_pfo_recovers() -> None:
    """A_PRIME ACTIVE hold: campaign PFO recovery MUST await return-ON writer.

    Patches both hold PG-write seams so unit stays mock-only; asserts
    ``apply_ab_hold_pfo_recovery_ons`` was awaited with recovered keyword ids.
    """
    adv_setting = SimpleNamespace(
        id=20,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        card_ab_hold_phase=None,
        max_price_for_order=100.0,
        card_ab_hold_allowed_phrases_snapshot=["confirmed-kw"],
        card_ab_hold_degraded=False,
    )
    recovered = _recovered_pass_keyword(ks_id=101)
    complex_adv = SimpleNamespace(
        adv_id=10,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
        adv_setting=adv_setting,
        fact_pay_for_order=50.0,  # recovered — not deep overspend
        get_keywords=AsyncMock(return_value=[recovered]),
    )

    enforce_mock = AsyncMock(
        return_value={"targets": 1, "written": 0, "cap_exceeded": []}
    )
    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = enforce_mock
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    off_mock = AsyncMock(return_value=0)
    recovery_on_mock = AsyncMock(return_value=1)

    with (
        patch(
            f"{_PIPELINES}.MinusPhraseManagerContainer",
            MagicMock(return_value=container),
        ),
        patch(f"{_PIPELINES}.apply_ab_hold_overspend_offs", off_mock),
        patch(f"{_PIPELINES}.apply_ab_hold_pfo_recovery_ons", recovery_on_mock),
    ):
        await process_ab_hold(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=True,
        )

    off_mock.assert_not_awaited()
    recovery_on_mock.assert_awaited_once_with(
        adv_id=10,
        keyword_ids=[101],
        confirmed_target_places=None,
    )
