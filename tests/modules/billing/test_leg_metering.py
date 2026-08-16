"""Unit-тесты leg_metering: якорь, gate, веса слотов (spec billing-fair-leg-pause)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.billing.leg_metering import (
    compute_anchor_billables,
    effective_count_from_billables,
    instant_leg_weight,
    resolve_metering_anchors,
)


def _adv(
    *,
    id_: int,
    adv_id: int | None,
    bot_active: bool = False,
    search_adv_id: int | None = None,
    active_status: str = "paused",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=id_,
        adv_id=adv_id,
        bot_active=bot_active,
        search_adv_id=search_adv_id,
        active_status=active_status,
    )


@pytest.mark.unit
def test_bot_inactive_not_in_effective_count() -> None:
    """S1: bot_active=False на якоре → комплект не входит в effective_count."""
    advs = [_adv(id_=1, adv_id=100, bot_active=False, active_status="started")]
    assert resolve_metering_anchors(advs) == []
    assert effective_count_from_billables([]) == 0.0


@pytest.mark.unit
def test_bot_active_included_when_started() -> None:
    """S2: bot_active=True и started → учитывается в effective_count."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="started"),
    ]
    anchors = resolve_metering_anchors(advs)
    assert len(anchors) == 1
    auto_w, search_w = __import__(
        "app.modules.billing.leg_metering", fromlist=["instant_anchor_weights"]
    ).instant_anchor_weights(anchors[0])
    assert auto_w == 0.5
    assert search_w == 0.5


@pytest.mark.unit
def test_search_row_never_anchor() -> None:
    """S3: Search-строка с bot_active не становится якорем."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=True, active_status="started"),
    ]
    anchors = resolve_metering_anchors(advs)
    anchor_ids = {a.anchor.id for a in anchors}
    assert 1 in anchor_ids
    assert 2 not in anchor_ids


@pytest.mark.unit
def test_no_search_pair_only_auto_slot() -> None:
    """S4: нет Search-ноги → только Auto-слот."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=999,
            active_status="started",
        ),
    ]
    anchors = resolve_metering_anchors(advs)
    assert len(anchors) == 1
    assert anchors[0].search_row is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_both_legs_started_full_unit() -> None:
    """S5: обе ноги started → per_anchor_units=1.0."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="started"),
    ]
    anchors = resolve_metering_anchors(advs)
    billables = await compute_anchor_billables(anchors)
    assert billables[0].total == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_only_anchor_started_half() -> None:
    """S6: только якорная started → 0.5."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="paused"),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert billables[0].total == 0.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_only_search_started_half() -> None:
    """S7: только Search started → 0.5."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="paused",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="started"),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert billables[0].total == 0.5


@pytest.mark.unit
@pytest.mark.asyncio
async def test_both_not_started_zero() -> None:
    """S8: обе не started → 0."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="paused",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="paused"),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert billables[0].total == 0.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_no_search_anchor_started_half() -> None:
    """S9: без Search, якорь started → 0.5."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=None,
            active_status="started",
        ),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert billables[0].total == 0.5
    assert not billables[0].has_search_slot


@pytest.mark.unit
@pytest.mark.asyncio
async def test_two_half_units_effective_count_one() -> None:
    """S10: два комплекта по 0.5 → effective_count=1.0."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="paused"),
        _adv(
            id_=3,
            adv_id=300,
            bot_active=True,
            search_adv_id=400,
            active_status="paused",
        ),
        _adv(id_=4, adv_id=400, bot_active=False, active_status="started"),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert effective_count_from_billables(billables) == 1.0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_search_paused_half_for_setup() -> None:
    """S17: Search на паузе, якорь started → 0.5 (read-only статус)."""
    advs = [
        _adv(
            id_=1,
            adv_id=100,
            bot_active=True,
            search_adv_id=200,
            active_status="started",
        ),
        _adv(id_=2, adv_id=200, bot_active=False, active_status="pause"),
    ]
    billables = await compute_anchor_billables(resolve_metering_anchors(advs))
    assert billables[0].auto_weight == 0.5
    assert billables[0].search_weight == 0.0
    assert billables[0].total == 0.5


@pytest.mark.unit
def test_instant_leg_weight_started() -> None:
    assert instant_leg_weight("started") == 0.5
    assert instant_leg_weight("paused") == 0.0
