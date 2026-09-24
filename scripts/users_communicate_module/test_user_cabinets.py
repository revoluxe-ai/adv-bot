"""Test-only builders for attaching lightweight mock cabinets to users.

This module is used by test message sending flows where loading all real user
shops is too expensive. It creates a small deterministic set of transient SQL
model instances and converts them into lightweight DTOs without extra DB or
ClickHouse calls.
"""

from __future__ import annotations

from scripts.users_csv_exporter.dto import UserCabinetDTO, UserDTO

from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User

DEFAULT_TEST_CABINETS_COUNT = 3
DEFAULT_TEST_CAMPAIGNS_PER_CABINET = 2
_TEST_TARIFF_PER_CAMPAIGN = 1_500.0
_TEST_BALANCE_BASE = 20_000.0
_TEST_BALANCE_STEP = 3_500.0
_TEST_BONUS_BASE = 1_000.0


def build_test_user_cabinets(
    user: User,
    *,
    cabinets_count: int = DEFAULT_TEST_CABINETS_COUNT,
    campaigns_per_cabinet: int = DEFAULT_TEST_CAMPAIGNS_PER_CABINET,
) -> list[WBUserCabinet]:
    """Return transient mock cabinets and campaigns for a test user.

    The returned objects are plain SQLAlchemy model instances that are not
    persisted to the database. They exist only to provide a compact and stable
    structure for test message generation.
    """
    safe_cabinets_count = max(1, cabinets_count)
    safe_campaigns_per_cabinet = max(1, campaigns_per_cabinet)
    user_id = user.id or 0

    cabinets: list[WBUserCabinet] = []
    for cabinet_index in range(1, safe_cabinets_count + 1):
        cabinet_id = user_id * 100 + cabinet_index
        wb_cabinet = WBCabinet(
            id=cabinet_id,
            shop_id=f"test-shop-{user_id}-{cabinet_index}",
            balance=_TEST_BALANCE_BASE + cabinet_index * _TEST_BALANCE_STEP,
            bonus=_TEST_BONUS_BASE,
        )
        wb_cabinet.balance_payments = []
        wb_cabinet.bonus_payments = []

        adv_settings: list[AdvSetting] = []
        for campaign_index in range(1, safe_campaigns_per_cabinet + 1):
            adv_id = cabinet_id * 100 + campaign_index
            adv_settings.append(
                AdvSetting(
                    id=adv_id,
                    adv_id=adv_id,
                    name=f"Test campaign {cabinet_index}.{campaign_index}",
                    wb_cabinet_id=cabinet_id,
                    bot_active=True,
                    active_status="started",
                    nmids=[adv_id],
                )
            )
        wb_cabinet.adv_settings = adv_settings

        wb_user_cabinet = WBUserCabinet(
            id=cabinet_id,
            wb_cabinet_id=cabinet_id,
            user_id=user_id,
            name=f"Test cabinet {cabinet_index}",
        )
        wb_user_cabinet.wb_cabinet = wb_cabinet
        cabinets.append(wb_user_cabinet)

    return cabinets


def build_test_user_dto(
    user: User,
    *,
    cabinets_count: int = DEFAULT_TEST_CABINETS_COUNT,
    campaigns_per_cabinet: int = DEFAULT_TEST_CAMPAIGNS_PER_CABINET,
) -> UserDTO:
    """Build a lightweight test DTO from mock cabinet SQL models."""
    user_cabinets = build_test_user_cabinets(
        user,
        cabinets_count=cabinets_count,
        campaigns_per_cabinet=campaigns_per_cabinet,
    )

    cabinets_dto: list[UserCabinetDTO] = []
    for wb_user_cabinet in user_cabinets:
        cabinet = wb_user_cabinet.wb_cabinet
        active_campaigns = sum(
            1 for adv in getattr(cabinet, "adv_settings", []) if adv.bot_active
        )
        tariff_total_per_month = active_campaigns * _TEST_TARIFF_PER_CAMPAIGN
        tariff_total_per_day = round(tariff_total_per_month / 30, 2)
        balance_plus_bonus = float(cabinet.balance) + float(cabinet.bonus)

        cabinets_dto.append(
            UserCabinetDTO(
                cabinet_name=wb_user_cabinet.name,
                shop_id=cabinet.shop_id,
                balance=float(cabinet.balance),
                bonus=float(cabinet.bonus),
                balance_plus_bonus=balance_plus_bonus,
                active_campaigns=active_campaigns,
                has_active_campaign=active_campaigns > 0,
                tariff_mode="auto",
                tariff_count=active_campaigns,
                tariff_price_per_adv=_TEST_TARIFF_PER_CAMPAIGN,
                tariff_total_per_month=tariff_total_per_month,
                tariff_total_per_day=tariff_total_per_day,
                balance_days_left=(
                    balance_plus_bonus / tariff_total_per_day
                    if tariff_total_per_day
                    else None
                ),
                last_30_days_topups=0.0,
                last_30_days_orders_sum_rub=0.0,
                last_30_days_buyouts_sum_rub=0.0,
            )
        )

    return UserDTO(
        user_id=user.id,
        telegram_id=user.user_telegram_id,
        login=user.username or "",
        cabinets=cabinets_dto,
    )
