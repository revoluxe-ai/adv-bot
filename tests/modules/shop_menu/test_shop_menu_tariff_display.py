from datetime import date, datetime, timezone
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.billing.pricer.pricer import TariffDetails, TariffMode
from app.modules.shop_menu.message import ShopMenu

pytestmark = pytest.mark.unit


class TestShopMenuTariffDisplay:
    def test_shop_menu_text_contains_tariff_mode_and_numbers(self):
        menu = ShopMenu(bot=None, chat_id=1, state=None, wb_user_cabinet_original_id=1)  # type: ignore[arg-type]
        m = cast(Any, menu)
        m._wb_user_cabinet = type("WBUC", (), {"name": "Test Shop", "id": 1})()
        m._wb_cabinet = type("WBC", (), {"shop_id": "shop_1", "id": 1, "active": True})()
        m._balance = 1000.0
        m._bonus = 0.0
        m._total_active_advs_count = 2
        m._last_charge_at = datetime(2025, 12, 16, 12, 34, 56)
        m._tariff_details = TariffDetails(
            mode=TariffMode.AUTO,
            count=2,
            price_per_adv=5000.0,
            total_per_month=10000.0,
            total_per_day=333.33,
        )

        text = menu.text
        assert "Тариф" in text
        assert "Новый тариф (Авто)" in text
        assert "Кампаний на автоуправлении" in text
        assert "10000.00" in text
        assert "Последнее списание" in text

    def test_cashback_snapshot_line_is_compact(self):
        line = ShopMenu._format_cashback_snapshot_line(  # type: ignore[attr-defined]
            {
                "cashbacks_total": 143497,
                "cashbacks_best_percent": 50,
                "cashbacks_earliest_expiration": "2026-04-03T21:00:00Z",
            }
        )

        assert line is not None
        assert "Cashback" in line
        assert "143497" in line
        assert "50%" in line
        # 2026-04-03T21:00:00Z == 2026-04-04 00:00 MSK — date label must follow Moscow calendar day
        assert "04.04.2026" in line

    def test_shop_menu_text_uses_active_fallback_when_attribute_absent(self):
        menu = ShopMenu(bot=None, chat_id=1, state=None, wb_user_cabinet_original_id=1)  # type: ignore[arg-type]
        m = cast(Any, menu)
        m._wb_user_cabinet = type("WBUC", (), {"name": "Shop Fallback", "id": 11})()
        # intentionally no `active` attribute
        m._wb_cabinet = type(
            "WBC", (), {"shop_id": "shop_fallback", "id": 22, "default_max_cpm": 1500}
        )()
        m._balance = 0.0
        m._bonus = 0.0
        m._total_active_advs_count = 0
        m._last_charge_at = None
        m._tariff_details = None
        m._token_status = None
        m._token_status_loaded = False
        m._shop_balance_snapshot = None

        text = menu.text
        assert "Статус магазина в боте" in text
        assert "Активен" in text

    def test_shop_menu_keyboard_uses_active_fallback_when_attribute_absent(self):
        menu = ShopMenu(bot=None, chat_id=1, state=None, wb_user_cabinet_original_id=1)  # type: ignore[arg-type]
        m = cast(Any, menu)
        # non-admin .user: keyboard path must not AttributeError; admin toggle absent
        m._wb_user_cabinet = type(
            "WBUC",
            (),
            {
                "name": "Shop Fallback",
                "id": 11,
                "user": type("User", (), {"user_telegram_id": 1_000_001})(),
            },
        )()
        # intentionally no `active` attribute
        m._wb_cabinet = type(
            "WBC",
            (),
            {
                "shop_id": "shop_fallback",
                "id": 22,
                "default_max_cpm": 1500,
                "white_list_update_active": False,
            },
        )()

        kb = menu.keyboard
        rows = kb.inline_keyboard
        flat_texts = [btn.text for row in rows for btn in row]
        assert "Деактивировать магазин" in flat_texts


@pytest.mark.asyncio
async def test_load_tariff_preview_passes_leg_latch_and_utc_date() -> None:
    """PBH-002: shop menu preview MUST use latch read, not instant weights only."""
    menu = ShopMenu(bot=None, chat_id=1, state=None, wb_user_cabinet_original_id=1)  # type: ignore[arg-type]
    m = cast(Any, menu)
    m._wb_cabinet = type("WBC", (), {"shop_id": "shop_latch"})()

    mock_latch = MagicMock()
    mock_billing_redis = MagicMock()
    mock_billing_redis.leg_latch.return_value = mock_latch
    m._billing_redis_manager = mock_billing_redis

    captured: dict[str, object] = {}

    async def _fake_get_tariff_details(
        session: object,
        shop_id: str,
        *,
        leg_latch: object = None,
        utc_date: date | None = None,
        **kwargs: object,
    ) -> TariffDetails:
        captured["shop_id"] = shop_id
        captured["leg_latch"] = leg_latch
        captured["utc_date"] = utc_date
        return TariffDetails(
            mode=TariffMode.AUTO,
            count=1.0,
            price_per_adv=100.0,
            total_per_month=100.0,
            total_per_day=3.33,
        )

    m._pricer = MagicMock()
    m._pricer.get_tariff_details = AsyncMock(side_effect=_fake_get_tariff_details)

    fixed_now = datetime(2025, 6, 15, 14, 30, tzinfo=timezone.utc)
    with patch("app.modules.shop_menu.message.sm") as mock_sm, patch(
        "app.modules.shop_menu.message.datetime"
    ) as mock_datetime:
        mock_datetime.now.return_value = fixed_now
        mock_session = AsyncMock()
        mock_sm.return_value.__aenter__.return_value = mock_session

        await m._load_tariff_preview()

    assert captured["shop_id"] == "shop_latch"
    assert captured["leg_latch"] is mock_latch
    assert captured["utc_date"] == fixed_now.date()
    m._pricer.get_tariff_details.assert_awaited_once()

