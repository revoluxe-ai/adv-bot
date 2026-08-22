"""PBH-001 / decision §17: stale stats MUST freeze epoch-managed setup FAIL→OFF.

Spec ``card-ab-hold-mode`` / tasks 23.8: ``process_ab_setup`` with
``stats_fresh=False`` MUST NOT call ``apply_ab_hold_setup_mutations``;
paired positive when fresh. Does not block PBH-005 apply/sync (epoch path).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
    CardAbHoldPhase,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.pipelines import (
    process_ab_setup,
    process_ab_setup_then_epoch,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import (
    KeywordStatus,
)

_PIPELINES = (
    "app.modules.shop_runner.service_manager.services.auto_updater_v3."
    "card_ab_hold.pipelines"
)


def _fail_keyword(*, ks_id: int = 101) -> SimpleNamespace:
    """Ключ Classification FAIL (PFO > max) — кандидат на OFF при fresh."""
    return SimpleNamespace(
        keyword_setting_original_id=ks_id,
        text="fail-kw-pfo",
        views=200,
        pay_for_order=150.0,
        position=12.0,
        status=KeywordStatus.GOOD,
    )


def _epoch_pending_adv() -> SimpleNamespace:
    """PENDING_SETUP + non-NULL phase (epoch-managed ENTER)."""
    adv_setting = SimpleNamespace(
        id=20,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        card_ab_hold_phase=CardAbHoldPhase.WARM_UP.value,
        max_price_for_order=100.0,
    )
    return SimpleNamespace(
        adv_id=10,
        shop_id=1,
        card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
        adv_setting=adv_setting,
        get_keywords=AsyncMock(return_value=[_fail_keyword()]),
        search_adv_id=None,
        nmids=[],
        min_nmids_bids=None,
    )


async def _run_epoch_setup(
    *,
    stats_fresh: bool,
) -> AsyncMock:
    """Прогнать epoch-managed ``process_ab_setup``; вернуть apply mock."""
    complex_adv = _epoch_pending_adv()
    lock_mgr = MagicMock()
    lock_mgr.acquire = AsyncMock(return_value=True)
    lock_mgr.release = AsyncMock(return_value=None)
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
        patch(f"{_PIPELINES}.RedisLockManager", MagicMock(return_value=lock_mgr)),
        patch(f"{_PIPELINES}.apply_ab_hold_setup_mutations", apply_mock),
    ):
        await process_ab_setup(
            complex_adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=stats_fresh,
        )
    return apply_mock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_stale_stats_freezes_epoch_managed_setup_fail_off() -> None:
    """PBH-001: ``stats_fresh=False`` → apply/FAIL→OFF MUST NOT run."""
    apply_mock = await _run_epoch_setup(stats_fresh=False)
    apply_mock.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_fresh_stats_allows_epoch_managed_setup_fail_off() -> None:
    """Paired positive: ``stats_fresh=True`` → apply(epoch_managed=True)."""
    apply_mock = await _run_epoch_setup(stats_fresh=True)
    apply_mock.assert_awaited()
    assert apply_mock.await_args.kwargs.get("epoch_managed") is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_setup_then_epoch_forwards_stats_fresh_to_setup() -> None:
    """``process_ab_setup_then_epoch`` MUST pass ``stats_fresh`` into setup."""
    seen: dict[str, Any] = {}
    adv = _epoch_pending_adv()

    async def _setup(*_a: Any, **kwargs: Any) -> None:
        seen["setup_stats_fresh"] = kwargs.get("stats_fresh")

    async def _epoch(*_a: Any, **kwargs: Any) -> None:
        seen["epoch_stats_fresh"] = kwargs.get("stats_fresh")

    with (
        patch(f"{_PIPELINES}.process_ab_setup", new=_setup),
        patch(
            "app.modules.shop_runner.service_manager.services.auto_updater_v3."
            "card_ab_hold.epoch_pipelines.process_ab_epoch",
            new=_epoch,
        ),
    ):
        await process_ab_setup_then_epoch(
            adv,  # type: ignore[arg-type]
            wb_shop_data_manager=MagicMock(),
            wb_manager_hub=MagicMock(),
            stats_fresh=False,
        )

    assert seen.get("setup_stats_fresh") is False
    assert seen.get("epoch_stats_fresh") is False
