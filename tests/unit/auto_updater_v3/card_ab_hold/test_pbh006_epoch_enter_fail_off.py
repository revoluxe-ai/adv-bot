"""PBH-006 RED: epoch-managed ENTER must still apply Classification FAIL->OFF.

Desired contract (tasks §18.4.2 / setup_apply epoch_managed=True):
non-NULL ``card_ab_hold_phase`` MUST NOT skip ``apply_ab_hold_setup_mutations``
entirely — FAIL keywords (PFO>, views<100, missing PFO) MUST turn OFF without
TP/ACTIVE.

Current bug: ``process_ab_setup`` early-returns when ``is_epoch_managed_ab_hold``
before classify/apply, so FAIL keywords stay ON through WARM_UP/confirm.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_setup,
)

_PIPELINES = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.pipelines"
)


def _fail_keyword(*, ks_id: int = 101) -> SimpleNamespace:
    """Ключ Classification FAIL (PFO > max) — MUST получить OFF на ENTER."""
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        text="fail-kw-pfo",
        views=200,
        pay_for_order=150.0,
        position=12.0,
        status=KeywordStatus.GOOD,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pbh006_epoch_managed_enter_applies_fail_off() -> None:
    """PBH-006 / §18.4.2: epoch-managed ENTER MUST call apply(epoch_managed=True).

    Encodes desired contract (not the buggy skip): Classification FAIL->OFF
    still happens on epoch-managed ENTER without TP/ACTIVE.
    """
    adv_setting = SimpleNamespace(
        id=20,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.AWAITING_KEYWORD_CONFIRM.value,
        max_price_for_order=100.0,
    )
    fail_kw = _fail_keyword()
    complex_adv = SimpleNamespace(
        adv_id=10,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        get_keywords=AsyncMock(return_value=[fail_kw]),
        search_adv_id=None,
        nmids=[],
        min_nmids_bids=None,
    )

    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)

    enforce_mock = AsyncMock(
        return_value={"targets": 1, "written": 0, "cap_exceeded": []}
    )
    mgr = MagicMock()
    mgr.enforce_frozen_allowed_set = enforce_mock
    container = MagicMock()
    container.minus_phrase_manager.return_value = mgr

    apply_mock = AsyncMock(return_value=(0, 1))

    with (
        patch(
            f"{_PIPELINES}.ensure_search_common_bid_reset_on_enter",
            new_callable=AsyncMock,
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSignalRedisCache",
            MagicMock(return_value=SimpleNamespace(client=MagicMock())),
        ),
        patch(
            f"{_PIPELINES}.CardAbHoldSetupBlockRedisCache",
            MagicMock(
                return_value=MagicMock(set_block=AsyncMock(), clear=AsyncMock())
            ),
        ),
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(
            f"{_PIPELINES}.MinusPhraseManagerContainer",
            MagicMock(return_value=container),
        ),
        patch(f"{_PIPELINES}.apply_ab_hold_setup_mutations", apply_mock),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
        )

    apply_mock.assert_awaited()
    kwargs = apply_mock.await_args.kwargs
    assert kwargs.get("epoch_managed") is True, (
        "epoch-managed ENTER must call apply_ab_hold_setup_mutations "
        "with epoch_managed=True so Classification FAIL->OFF still runs "
        "without TP/ACTIVE (PBH-006 / tasks §18.4.2)"
    )
    assert (
        complex_adv.adv_setting.card_ab_hold_mode
        == CardAbHoldMode.PENDING_SETUP.value
    )
