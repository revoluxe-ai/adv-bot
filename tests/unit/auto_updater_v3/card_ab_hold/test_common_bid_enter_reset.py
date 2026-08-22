"""Tasks §27: ENTER Search common-bid reset-to-min then freeze (decision §19).

Spec requirement «ENTER resets Search common bid to WB minimum then freezes it».
Owned path = ``ensure_search_common_bid_reset_on_enter`` (setup/epoch), NOT
ordinary ``update_common_bid_in_search_adv``. Ordinary freeze covered by
PBH-004 suite; bidder remains eligible in ACTIVE.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.mp.wb.api.adapter.promotion_client.common_bids.command import (
    SetCommonBidsCommand,
)
from app.core.mp.wb.dto.adv_min_bids import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.common_bid_enter_reset import (
    build_set_common_bids_to_min_command,
    ensure_search_common_bid_reset_on_enter,
    resolve_search_min_bids_for_nmids,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.mode import (
    CardAbHoldMode,
)
from app.modules.shop_runner.service_manager.services.auto_updater_v3.card_ab_hold.scheduling import (
    filter_bidder_eligible_by_ab_hold,
    filter_structural_act_candidates,
    should_allow_bidder_on_ab_hold,
)


def _adv_setting(*, adv_id: int = 101) -> SimpleNamespace:
    """Minimal AdvSetting shape for Redis cache unique_id."""
    return SimpleNamespace(adv_id=adv_id, id=adv_id, card_ab_hold_phase=None)


def _complex_adv(
    *,
    mode: str,
    nmids: list[int] | None = None,
    search_min: dict[int, int] | None = None,
    search_adv_id: int | None = 9001,
    adv_id: int = 101,
) -> SimpleNamespace:
    """Production-like ComplexAdv stub for ENTER common-bid reset."""
    nm = nmids if nmids is not None else [11, 22]
    min_bids = (
        AdvMinNmidsBids(auto={}, search=dict(search_min))
        if search_min is not None
        else None
    )
    setting = _adv_setting(adv_id=adv_id)
    return SimpleNamespace(
        adv_id=adv_id,
        card_ab_hold_mode=mode,
        adv_setting=setting,
        nmids=nm,
        search_adv_id=search_adv_id,
        min_nmids_bids=min_bids,
    )


@pytest.mark.unit
def test_resolve_search_min_bids_for_all_nmids() -> None:
    """§27.1 helper: SoT minima resolve for every campaign nmid."""
    mins = AdvMinNmidsBids(auto={11: 50}, search={11: 100, 22: 120})
    assert resolve_search_min_bids_for_nmids(nmids=[11, 22], min_nmids_bids=mins) == {
        11: 100,
        22: 120,
    }


@pytest.mark.unit
def test_resolve_search_min_bids_missing_returns_none() -> None:
    """Visible degrade path: incomplete min SoT → None (retry, not silent OK)."""
    mins = AdvMinNmidsBids(auto={}, search={11: 100})
    assert (
        resolve_search_min_bids_for_nmids(nmids=[11, 22], min_nmids_bids=mins) is None
    )
    assert resolve_search_min_bids_for_nmids(nmids=[11], min_nmids_bids=None) is None


@pytest.mark.unit
def test_build_set_common_bids_to_min_command_items() -> None:
    """Owned path builds SetCommonBids for SEARCH nmids at min."""
    adv = _complex_adv(
        mode=CardAbHoldMode.PENDING_SETUP.value,
        search_min={11: 100, 22: 120},
    )
    cmd = build_set_common_bids_to_min_command(adv, {11: 100, 22: 120})
    assert isinstance(cmd, SetCommonBidsCommand)
    assert [i.target_nmid for i in cmd.items] == [11, 22]
    assert [i.new_bid for i in cmd.items] == [100, 120]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_enter_reset_writes_wb_min_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """§27.1: PENDING_SETUP owned path → WB SetCommonBids at min + done marker."""
    adv = _complex_adv(
        mode=CardAbHoldMode.PENDING_SETUP.value,
        search_min={11: 100, 22: 120},
    )
    wb_write = AsyncMock()
    redis_set = AsyncMock()
    done = {"v": False}

    class _DoneCache:
        def __init__(self, _adv: object) -> None:
            pass

        async def is_done(self) -> bool:
            return done["v"]

        async def mark_done(self) -> None:
            done["v"] = True

    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.CardAbHoldCommonBidEnterResetRedisCache",
        _DoneCache,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.RedisCommonBidValueManager",
        lambda _client: SimpleNamespace(set_bids=redis_set),
    )
    hub = SimpleNamespace(
        wb_modifier=SimpleNamespace(update_search_adv_common_cpm=wb_write),
        redis_client_wrapper=MagicMock(),
    )

    first = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert first.status == "written"
    assert first.nmid_to_bid == {11: 100, 22: 120}
    wb_write.assert_awaited_once()
    redis_set.assert_awaited_once()
    assert done["v"] is True

    second = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert second.status == "already_done"
    assert wb_write.await_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mid_hold_active_does_not_owned_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§27.3: ACTIVE (mid-hold) → skipped_wrong_mode; no WB write."""
    adv = _complex_adv(
        mode=CardAbHoldMode.ACTIVE.value,
        search_min={11: 100},
    )
    wb_write = AsyncMock()
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.CardAbHoldCommonBidEnterResetRedisCache",
        lambda _adv: SimpleNamespace(
            is_done=AsyncMock(return_value=False),
            mark_done=AsyncMock(),
        ),
    )
    hub = SimpleNamespace(
        wb_modifier=SimpleNamespace(update_search_adv_common_cpm=wb_write),
        redis_client_wrapper=MagicMock(),
    )
    result = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert result.status == "skipped_wrong_mode"
    wb_write.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_exit_clears_done_allows_new_enter_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§27.3 paired: after EXIT clear, new ENTER PENDING may write again."""
    adv = _complex_adv(
        mode=CardAbHoldMode.PENDING_SETUP.value,
        nmids=[11],
        search_min={11: 90},
    )
    done = {"v": True}  # as if previous episode completed
    wb_write = AsyncMock()

    class _DoneCache:
        def __init__(self, _adv: object) -> None:
            pass

        async def is_done(self) -> bool:
            return done["v"]

        async def mark_done(self) -> None:
            done["v"] = True

        async def clear(self) -> None:
            done["v"] = False

    cache_cls = _DoneCache
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.CardAbHoldCommonBidEnterResetRedisCache",
        cache_cls,
    )
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.RedisCommonBidValueManager",
        lambda _client: SimpleNamespace(set_bids=AsyncMock()),
    )
    hub = SimpleNamespace(
        wb_modifier=SimpleNamespace(update_search_adv_common_cpm=wb_write),
        redis_client_wrapper=MagicMock(),
    )

    blocked = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert blocked.status == "already_done"
    wb_write.assert_not_awaited()

    await cache_cls(adv.adv_setting).clear()  # EXIT
    again = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert again.status == "written"
    wb_write.assert_awaited_once()


@pytest.mark.unit
def test_ordinary_common_bid_still_structurally_frozen() -> None:
    """§27.2: PENDING/ACTIVE dropped before ordinary common-bid write set."""
    pool = [
        SimpleNamespace(
            adv_id=1,
            card_ab_hold_mode=CardAbHoldMode.OFF.value,
            bot_active=True,
        ),
        SimpleNamespace(
            adv_id=2,
            card_ab_hold_mode=CardAbHoldMode.PENDING_SETUP.value,
            bot_active=True,
        ),
        SimpleNamespace(
            adv_id=3,
            card_ab_hold_mode=CardAbHoldMode.ACTIVE.value,
            bot_active=True,
        ),
    ]
    allowed = filter_structural_act_candidates(pool)
    assert [a.adv_id for a in allowed] == [1]


@pytest.mark.unit
def test_bidder_remains_eligible_in_active_while_common_bid_frozen() -> None:
    """§27.4: bidder Allowed in ACTIVE; ordinary common-bid Forbidden."""
    assert should_allow_bidder_on_ab_hold(CardAbHoldMode.ACTIVE) is True
    pool = [
        SimpleNamespace(adv_id=1, card_ab_hold_mode=CardAbHoldMode.ACTIVE.value),
        SimpleNamespace(adv_id=2, card_ab_hold_mode=CardAbHoldMode.OFF.value),
    ]
    eligible = filter_bidder_eligible_by_ab_hold(pool)
    assert {a.adv_id for a in eligible} == {1, 2}
    structural = filter_structural_act_candidates(pool)
    assert [a.adv_id for a in structural] == [2]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_missing_min_bids_degrades_without_done(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """§27.5: missing min → degraded_missing_min, done NOT set (retry)."""
    adv = _complex_adv(
        mode=CardAbHoldMode.PENDING_SETUP.value,
        search_min=None,
    )
    marked = {"v": False}
    monkeypatch.setattr(
        "app.modules.shop_runner.service_manager.services.auto_updater_v3."
        "card_ab_hold.common_bid_enter_reset.CardAbHoldCommonBidEnterResetRedisCache",
        lambda _adv: SimpleNamespace(
            is_done=AsyncMock(return_value=False),
            mark_done=AsyncMock(side_effect=lambda: marked.__setitem__("v", True)),
        ),
    )
    hub = SimpleNamespace(
        wb_modifier=SimpleNamespace(update_search_adv_common_cpm=AsyncMock()),
        redis_client_wrapper=MagicMock(),
    )
    result = await ensure_search_common_bid_reset_on_enter(adv, wb_manager_hub=hub)
    assert result.status == "degraded_missing_min"
    assert marked["v"] is False
    hub.wb_modifier.update_search_adv_common_cpm.assert_not_awaited()
