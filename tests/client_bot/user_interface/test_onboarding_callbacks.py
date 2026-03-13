"""Unit tests for onboarding callbacks: ShowShopsList, ShopsListPaginator, Start, ConnectExisting*."""

from app.client_bot.user_interface.views.callbacks import (
    ConnectExistingAdvs,
    ConnectExistingAdvsBackToShop,
    ConnectExistingConfirmType1,
    ConnectExistingConfirmType2,
    ConnectExistingContinueDespiteInvalid,
    ConnectExistingCreateBoth,
    ShowShopsList,
    ShopsListPaginator,
    Start,
)


def test_show_shops_list_pack_starts_with_prefix() -> None:
    """ShowShopsList().pack() starts with shops_list:."""
    data = ShowShopsList().pack()
    assert data.startswith("shops_list")


def test_show_shops_list_unpack_roundtrip() -> None:
    """ShowShopsList pack/unpack roundtrip."""
    packed = ShowShopsList().pack()
    unpacked = ShowShopsList.unpack(packed)
    assert unpacked is not None


def test_shops_list_paginator_pack_contains_page() -> None:
    """ShopsListPaginator(page=2).pack() contains page, unpack returns page=2."""
    packed = ShopsListPaginator(page=2).pack()
    assert "2" in packed
    unpacked = ShopsListPaginator.unpack(packed)
    assert unpacked is not None
    assert unpacked.page == 2


def test_start_pack_starts_with_prefix() -> None:
    """Start().pack() starts with start:."""
    data = Start().pack()
    assert data.startswith("start")


def test_connect_existing_advs_pack_starts_with_prefix() -> None:
    """ConnectExistingAdvs().pack() starts with connect_existing_advs:."""
    data = ConnectExistingAdvs(wb_user_cabinet_original_id=42).pack()
    assert data.startswith("connect_existing_advs")


def test_connect_existing_advs_unpack_roundtrip() -> None:
    """ConnectExistingAdvs pack/unpack roundtrip preserves wb_user_cabinet_original_id."""
    packed = ConnectExistingAdvs(wb_user_cabinet_original_id=100).pack()
    unpacked = ConnectExistingAdvs.unpack(packed)
    assert unpacked is not None
    assert unpacked.wb_user_cabinet_original_id == 100


def test_connect_existing_confirm_type1_pack_unpack() -> None:
    """ConnectExistingConfirmType1 pack/unpack with adv_id (including 0)."""
    packed_zero = ConnectExistingConfirmType1(adv_id=0).pack()
    unpacked_zero = ConnectExistingConfirmType1.unpack(packed_zero)
    assert unpacked_zero is not None
    assert unpacked_zero.adv_id == 0

    packed_123 = ConnectExistingConfirmType1(adv_id=123).pack()
    unpacked_123 = ConnectExistingConfirmType1.unpack(packed_123)
    assert unpacked_123 is not None
    assert unpacked_123.adv_id == 123


def test_connect_existing_confirm_type2_pack_unpack() -> None:
    """ConnectExistingConfirmType2 pack/unpack with adv_id (including 0)."""
    packed_zero = ConnectExistingConfirmType2(adv_id=0).pack()
    unpacked_zero = ConnectExistingConfirmType2.unpack(packed_zero)
    assert unpacked_zero is not None
    assert unpacked_zero.adv_id == 0

    packed_456 = ConnectExistingConfirmType2(adv_id=456).pack()
    unpacked_456 = ConnectExistingConfirmType2.unpack(packed_456)
    assert unpacked_456 is not None
    assert unpacked_456.adv_id == 456


def test_connect_existing_create_both_pack_unpack() -> None:
    """ConnectExistingCreateBoth pack/unpack with action confirm/cancel."""
    packed_confirm = ConnectExistingCreateBoth(action="confirm").pack()
    unpacked_confirm = ConnectExistingCreateBoth.unpack(packed_confirm)
    assert unpacked_confirm is not None
    assert unpacked_confirm.action == "confirm"

    packed_cancel = ConnectExistingCreateBoth(action="cancel").pack()
    unpacked_cancel = ConnectExistingCreateBoth.unpack(packed_cancel)
    assert unpacked_cancel is not None
    assert unpacked_cancel.action == "cancel"


def test_connect_existing_continue_despite_invalid_pack_unpack() -> None:
    """ConnectExistingContinueDespiteInvalid pack/unpack with action confirm/cancel."""
    packed_confirm = ConnectExistingContinueDespiteInvalid(action="confirm").pack()
    unpacked_confirm = ConnectExistingContinueDespiteInvalid.unpack(packed_confirm)
    assert unpacked_confirm is not None
    assert unpacked_confirm.action == "confirm"

    packed_cancel = ConnectExistingContinueDespiteInvalid(action="cancel").pack()
    unpacked_cancel = ConnectExistingContinueDespiteInvalid.unpack(packed_cancel)
    assert unpacked_cancel is not None
    assert unpacked_cancel.action == "cancel"


def test_connect_existing_advs_back_to_shop_pack_unpack() -> None:
    """ConnectExistingAdvsBackToShop pack/unpack preserves wb_user_cabinet_original_id."""
    packed = ConnectExistingAdvsBackToShop(wb_user_cabinet_original_id=77).pack()
    unpacked = ConnectExistingAdvsBackToShop.unpack(packed)
    assert unpacked is not None
    assert unpacked.wb_user_cabinet_original_id == 77
