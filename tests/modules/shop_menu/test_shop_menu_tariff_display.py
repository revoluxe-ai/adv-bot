from datetime import datetime
from typing import Any, cast

from app.modules.billing.pricer.pricer import TariffDetails, TariffMode
from app.modules.shop_menu.message import ShopMenu


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

