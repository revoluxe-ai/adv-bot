from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.modules.shop_runner.service_manager.services.update_commot_bid_in_search_advs_manager.update_commot_bid_in_search_advs_manager import (
    UpdateCommotBidInSearchAdvsManager,
)


@dataclass
class FakeAdv:
    result_target_pay_for_order: float
    fact_pay_for_order: float
    current_common_bids_in_search_adv: dict[int, int] | None
    bid_step: int
    search_adv_min_bids: dict[int, int]
    max_user_cpm_bid: int


def make_adv(
    *,
    current_nmid: int = 100,
    current_bid: int = 120,
    fact_pay_for_order: float = 100.0,
    result_target_pay_for_order: float = 100.0,
    bid_step: int = 5,
    min_bid: int = 10,
    max_bid: int = 200,
    current_common_bids_override: dict[int, int] | None = None,
    use_none_for_bids: bool = False,
) -> FakeAdv:
    if use_none_for_bids:
        bids: dict[int, int] | None = None
    elif current_common_bids_override is not None:
        bids = current_common_bids_override
    else:
        bids = {current_nmid: current_bid}
    return FakeAdv(
        result_target_pay_for_order=result_target_pay_for_order,
        fact_pay_for_order=fact_pay_for_order,
        current_common_bids_in_search_adv=bids,
        bid_step=bid_step,
        search_adv_min_bids={current_nmid: min_bid},
        max_user_cpm_bid=max_bid,
    )


def test_get_new_bid_ignores_falsy_current_bid_zero() -> None:
    adv = make_adv(current_bid=0)

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="reset"
    )

    assert new_bid is None


def test_get_new_bid_uses_min_bid_when_current_common_bids_is_none() -> None:
    """When current_common_bids_in_search_adv is None, fallback to min_bid; reset yields min_bid, so no change."""
    adv = make_adv(
        use_none_for_bids=True,
        fact_pay_for_order=100.0,
        result_target_pay_for_order=100.0,
        min_bid=50,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct='reset'
    )

    assert new_bid is None  # current_bid becomes 50 (min), reset -> 50, no change


def test_get_new_bid_uses_min_bid_when_nmid_missing_in_current_common_bids() -> None:
    """When nmid is not in current_common_bids, fallback to min_bid; then reset gives min_bid."""
    adv = make_adv(
        current_common_bids_override={999: 200},  # different nmid, so 100 is missing
        fact_pay_for_order=100.0,
        result_target_pay_for_order=100.0,
        min_bid=50,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct='reset'
    )

    assert new_bid is None  # current_bid = min_bid 50, reset -> 50, no change


def test_get_new_bid_when_current_common_bids_none_direct_up_returns_min_plus_step() -> None:
    """When current_common_bids is None and direct is 'up', use min_bid as current then add step."""
    adv = make_adv(
        use_none_for_bids=True,
        fact_pay_for_order=80.0,
        result_target_pay_for_order=100.0,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct='up'
    )

    assert new_bid == 51  # current_bid = 50 (min), direct up -> 50 + 1 = 51


def test_get_new_bid_decreases_when_fact_above_target() -> None:
    """direct='reset' sets bid to search min (not stepped down from current)."""
    adv = make_adv(
        fact_pay_for_order=150.0,
        result_target_pay_for_order=100.0,
        current_bid=120,
        bid_step=7,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="reset"
    )

    assert new_bid == 50


def test_get_new_bid_increases_when_fact_below_target() -> None:
    """direct='up' adds 1 to current bid (fact < target)."""
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=100.0,
        current_bid=120,
        bid_step=10,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="up"
    )

    assert new_bid == 121


def test_get_new_bid_applies_minimum_clamp() -> None:
    adv = make_adv(
        fact_pay_for_order=200.0,
        result_target_pay_for_order=150.0,
        current_bid=55,
        bid_step=10,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="reset"
    )

    assert new_bid == 50


def test_get_new_bid_applies_maximum_clamp() -> None:
    """direct='up': current_bid+1 must not exceed max_bid; 194+1=195."""
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=150.0,
        current_bid=194,
        bid_step=20,
        min_bid=50,
        max_bid=195,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="up"
    )

    assert new_bid == 195  # 194 + 1 = 195, clamped to max_user_cpm_bid 195


def test_get_new_bid_returns_none_when_clamped_matches_current() -> None:
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=150.0,
        current_bid=195,
        bid_step=20,
        min_bid=50,
        max_bid=195,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="up"
    )

    assert new_bid is None


def test_get_new_bid_returns_int_when_fact_equals_target() -> None:
    """direct='reset' (fact == target) sets bid to min_bid."""
    adv = make_adv(
        fact_pay_for_order=123.0,
        result_target_pay_for_order=123.0,
        current_bid=140,
        bid_step=5,
        min_bid=90,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(
        adv, current_nmid=100, direct="reset"
    )

    assert isinstance(new_bid, int)
    assert new_bid == 90
