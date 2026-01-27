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
    current_common_bids_in_search_adv: dict[int, int]
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
) -> FakeAdv:
    return FakeAdv(
        result_target_pay_for_order=result_target_pay_for_order,
        fact_pay_for_order=fact_pay_for_order,
        current_common_bids_in_search_adv={current_nmid: current_bid},
        bid_step=bid_step,
        search_adv_min_bids={current_nmid: min_bid},
        max_user_cpm_bid=max_bid,
    )


@pytest.mark.parametrize("current_bid", [0, None])
def test_get_new_bid_ignores_falsy_current_bid(current_bid: int | None) -> None:
    adv = make_adv(current_bid=current_bid)

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid is None


def test_get_new_bid_decreases_when_fact_above_target() -> None:
    adv = make_adv(
        fact_pay_for_order=150.0,
        result_target_pay_for_order=100.0,
        current_bid=120,
        bid_step=7,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid == 113


def test_get_new_bid_increases_when_fact_below_target() -> None:
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=100.0,
        current_bid=120,
        bid_step=10,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid == 130


def test_get_new_bid_applies_minimum_clamp() -> None:
    adv = make_adv(
        fact_pay_for_order=200.0,
        result_target_pay_for_order=150.0,
        current_bid=55,
        bid_step=10,
        min_bid=50,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid == 50


def test_get_new_bid_applies_maximum_clamp() -> None:
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=150.0,
        current_bid=190,
        bid_step=20,
        min_bid=50,
        max_bid=195,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid == 195


def test_get_new_bid_returns_none_when_clamped_matches_current() -> None:
    adv = make_adv(
        fact_pay_for_order=80.0,
        result_target_pay_for_order=150.0,
        current_bid=195,
        bid_step=20,
        min_bid=50,
        max_bid=195,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert new_bid is None


def test_get_new_bid_returns_int_when_fact_equals_target() -> None:
    adv = make_adv(
        fact_pay_for_order=123.0,
        result_target_pay_for_order=123.0,
        current_bid=140,
        bid_step=5,
        min_bid=90,
        max_bid=200,
    )

    new_bid = UpdateCommotBidInSearchAdvsManager._get_new_bid(adv, current_nmid=100)

    assert isinstance(new_bid, int)
    assert new_bid == 123
