"""Unit-тесты use-case включения/выключения paid auto-management."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.client_bot.user_interface.services.adv_auto_management_activation import (
    PaidActivationBlockReason,
    activate_adv_paid_mode,
    check_paid_activation_eligibility,
    deactivate_adv_free_mode,
)
from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from tests.factories.adv_factory import AdvSettingFactory, WBCabinetFactory

pytestmark = pytest.mark.unit


@pytest.fixture
def wb_cabinet():
    return WBCabinetFactory.build(id=10, shop_id="shop-1")


@pytest.fixture
def session() -> MagicMock:
    mock_session = MagicMock()
    mock_session.commit = AsyncMock()
    return mock_session


def _patch_eligibility_deps(
    *,
    tariff_for_month: int = 3000,
    price_for_day: float = 100.0,
    balance: float = 500.0,
    bonus: float = 0.0,
    read_only_only: bool = False,
) -> ExitStack:
    stack = ExitStack()
    stack.enter_context(
        patch(
            "app.client_bot.user_interface.services.adv_auto_management_activation.pricer.get_price_for_day_for_shop",
            new=AsyncMock(return_value=tariff_for_month),
        )
    )
    stack.enter_context(
        patch(
            "app.client_bot.user_interface.services.adv_auto_management_activation.pricer.get_tariff_for_day",
            return_value=price_for_day,
        )
    )
    stack.enter_context(
        patch(
            "app.client_bot.user_interface.services.adv_auto_management_activation.balance_manager.get_cabinet_balance_and_bonuses",
            new=AsyncMock(return_value=(balance, bonus)),
        )
    )
    stack.enter_context(
        patch(
            "app.client_bot.user_interface.services.adv_auto_management_activation._shop_has_read_only_only_tokens",
            new=AsyncMock(return_value=read_only_only),
        )
    )
    return stack


@pytest.mark.asyncio
async def test_eligibility_blocks_zero_balance(session: MagicMock, wb_cabinet) -> None:
    with _patch_eligibility_deps(balance=0.0, bonus=0.0):
        result = await check_paid_activation_eligibility(session, wb_cabinet)

    assert result.allowed is False
    assert result.block_reason is PaidActivationBlockReason.ZERO_BALANCE


@pytest.mark.asyncio
async def test_eligibility_blocks_insufficient_for_day(
    session: MagicMock, wb_cabinet
) -> None:
    with _patch_eligibility_deps(balance=50.0, price_for_day=100.0):
        result = await check_paid_activation_eligibility(session, wb_cabinet)

    assert result.allowed is False
    assert result.block_reason is PaidActivationBlockReason.INSUFFICIENT_FOR_DAY


@pytest.mark.asyncio
async def test_eligibility_blocks_read_only_token(session: MagicMock, wb_cabinet) -> None:
    with _patch_eligibility_deps(read_only_only=True):
        result = await check_paid_activation_eligibility(session, wb_cabinet)

    assert result.allowed is False
    assert result.block_reason is PaidActivationBlockReason.READ_ONLY_TOKEN


@pytest.mark.asyncio
async def test_eligibility_allows_normal_shop(session: MagicMock, wb_cabinet) -> None:
    with _patch_eligibility_deps(balance=500.0, price_for_day=100.0):
        result = await check_paid_activation_eligibility(session, wb_cabinet)

    assert result.allowed is True
    assert result.block_reason is None


@pytest.mark.asyncio
async def test_eligibility_boundary_balance_equals_day_price(
    session: MagicMock, wb_cabinet
) -> None:
    with _patch_eligibility_deps(balance=100.0, price_for_day=100.0):
        result = await check_paid_activation_eligibility(session, wb_cabinet)

    assert result.allowed is True
    assert result.block_reason is None


@pytest.mark.asyncio
async def test_activate_applies_paid_transition_in_memory(
    session: MagicMock, wb_cabinet
) -> None:
    adv = AdvSettingFactory.build(
        bot_active=False,
        automatic_version=2,
        white_list_mode=WhiteListMode.ABOVE_MIN_RATING,
        bidder_active=False,
    )

    with patch(
        "app.client_bot.user_interface.services.adv_auto_management_activation.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ) as backfill_mock:
        await activate_adv_paid_mode(session, adv, wb_cabinet)

    assert adv.bot_active is True
    assert adv.automatic_version == 3
    assert adv.white_list_mode == WhiteListMode.REPLACE_ON_TRIM
    assert adv.bidder_active is True
    session.commit.assert_awaited_once()
    backfill_mock.assert_awaited_once_with(dry_run=False, adv_setting_id=adv.id)


@pytest.mark.asyncio
async def test_activate_does_not_apply_common_defaults(
    session: MagicMock, wb_cabinet
) -> None:
    adv = AdvSettingFactory.build(
        bot_active=False,
        automatic_version=2,
        bidder_coroutine_type=BidderCoroutineType.OLD_UPDATE_CPM_BIDDER,
        orders_source_for_auto_mode=OrdersSourceForAutoMode.ADV_SUM,
        sales_predict_method=FactMethods.DIRECT_SALES,
    )

    with patch(
        "app.client_bot.user_interface.services.adv_auto_management_activation.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ):
        await activate_adv_paid_mode(session, adv, wb_cabinet)

    assert adv.bidder_coroutine_type == BidderCoroutineType.OLD_UPDATE_CPM_BIDDER
    assert adv.orders_source_for_auto_mode == OrdersSourceForAutoMode.ADV_SUM
    assert adv.sales_predict_method == FactMethods.DIRECT_SALES


@pytest.mark.asyncio
async def test_activate_triggers_backfill_on_v2_to_v3(
    session: MagicMock, wb_cabinet
) -> None:
    adv = AdvSettingFactory.build(bot_active=False, automatic_version=2, id=42)

    with patch(
        "app.client_bot.user_interface.services.adv_auto_management_activation.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ) as backfill_mock:
        await activate_adv_paid_mode(session, adv, wb_cabinet)

    backfill_mock.assert_awaited_once_with(dry_run=False, adv_setting_id=42)


@pytest.mark.asyncio
async def test_activate_skips_backfill_when_already_v3(
    session: MagicMock, wb_cabinet
) -> None:
    adv = AdvSettingFactory.build(bot_active=False, automatic_version=3)

    with patch(
        "app.client_bot.user_interface.services.adv_auto_management_activation.backfill_v3_hard_statuses_and_states_consistency",
        new=AsyncMock(),
    ) as backfill_mock:
        await activate_adv_paid_mode(session, adv, wb_cabinet)

    backfill_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_deactivate_applies_free_transition(session: MagicMock, wb_cabinet) -> None:
    adv = AdvSettingFactory.build(
        bot_active=True,
        automatic_version=3,
        white_list_mode=WhiteListMode.REPLACE_ON_TRIM,
        auto_update_white_list=True,
        auto_update_target_place=True,
        bidder_for_auto=True,
        bidder_active=True,
        max_place=9,
        max_cpm=1234,
    )

    await deactivate_adv_free_mode(session, adv, wb_cabinet)

    assert adv.bot_active is False
    assert adv.automatic_version == 2
    assert adv.white_list_mode == WhiteListMode.ABOVE_MIN_RATING
    assert adv.auto_update_white_list is False
    assert adv.auto_update_target_place is False
    assert adv.bidder_for_auto is False
    assert adv.bidder_active is False
    assert adv.max_place == 9
    assert adv.max_cpm == 1234
    session.commit.assert_awaited_once()
