import csv
from io import StringIO
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.client_bot.utils import get_csv_file
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus


class DummyCalculatedKeyword:
    def __init__(
        self,
        *,
        text: str,
        clicks: int,
        views: int,
        total_views: int,
        query: str,
        predict_ctr: float,
        ctr: float,
        reason: str,
        hard_status: int,
        status: KeywordStatus,
        position: float,
        rating_by_orders: float,
        total_orders: int,
    ) -> None:
        self.text = text
        self.clicks = clicks
        self.views = views
        self.total_views = total_views
        self.query = query
        self.predict_ctr = predict_ctr
        self.ctr = ctr
        self.reason = reason
        self.hard_status = hard_status
        self.status = status
        self.position = position
        self.rating_by_orders = rating_by_orders
        self.total_orders = total_orders


@pytest.mark.asyncio
async def test_get_csv_file_generates_sorted_rows(monkeypatch: pytest.MonkeyPatch):
    """Убедиться, что CSV содержит заголовок и строки упорядочены по заказам."""
    adv_setting = MagicMock(spec=AdvSetting)
    adv_setting.parsing_active = True
    low_orders_keyword = DummyCalculatedKeyword(
        text="low_order_keyword",
        clicks=5,
        views=50,
        total_views=80,
        query="5",
        predict_ctr=0.24,
        ctr=0.1,
        reason="max_cpc",
        hard_status=1,
        status=KeywordStatus.GOOD,
        position=0.0,
        rating_by_orders=0.0,
        total_orders=5,
    )
    high_orders_keyword = DummyCalculatedKeyword(
        text="high_order_keyword",
        clicks=10,
        views=100,
        total_views=200,
        query="10",
        predict_ctr=0.6,
        ctr=0.2,
        reason="max_position",
        hard_status=1,
        status=KeywordStatus.GOOD,
        position=1.0,
        rating_by_orders=0.1,
        total_orders=10,
    )
    monkeypatch.setattr(
        "app.client_bot.utils.get_keywords_for_keyboard",
        AsyncMock(return_value=[low_orders_keyword, high_orders_keyword]),
    )

    csv_content = await get_csv_file(adv_setting)
    parsed = list(csv.reader(StringIO(csv_content), delimiter=";", quotechar='"'))

    assert parsed[0][0] == "Запрос(вхождение)"
    data_rows = parsed[1:]
    assert data_rows[0][0] == high_orders_keyword.text
    assert data_rows[1][0] == low_orders_keyword.text
    assert data_rows[0][8] == "ЦП"  # Статус (hard_status) теперь на индексе 8
    assert data_rows[1][8] == "МС"
    assert data_rows[0][-1] == str(high_orders_keyword.total_orders)
    assert data_rows[1][-1] == str(low_orders_keyword.total_orders)

