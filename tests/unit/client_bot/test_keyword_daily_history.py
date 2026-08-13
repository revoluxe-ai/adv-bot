"""Тесты экрана дневной истории одного ключевого запроса."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from app.client_bot.user_interface.views.callbacks import (
    KeywordDailyHistory,
    SettingKeyword,
)
from app.client_bot.user_interface.views.keyboards import (
    get_keyword_daily_history_keyboard,
)
from app.modules.wb_adv_updater.keyword_daily_history import (
    date_pagination,
)
from app.client_bot.user_interface.views.messages.adv_keyword_messages.keyword_daily_history_message import (
    build_keyword_daily_history_text,
    format_keyword_daily_stat_block,
)
from app.modules.wb_adv_updater.keyword_daily_history.dto import KeywordDailyStat
from app.modules.wb_adv_updater.keyword_daily_history.keyword_daily_history_manager import (
    KeywordDailyHistoryManager,
)


@pytest.mark.unit
def test_format_keyword_daily_stat_block_renders_metrics() -> None:
    """Блок дня должен показывать позицию, CPM, CTR и конверсии."""
    stat = KeywordDailyStat.model_validate(
        {
            "date": date(2026, 6, 16),
            "views": 1200,
            "clicks": 45,
            "add_to_cart": 8,
            "orders": 3,
            "spend": 294.0,
            "cpm": 245.0,
            "avg_pos": 12.4,
        }
    )

    text = format_keyword_daily_stat_block(stat)

    assert "16.06.2026" in text
    assert "Поз.: 12.4 | CPM: 245 ₽" in text
    assert "Показы: 1200 | Клики: 45 (3.75%)" in text
    assert "Корз.: 8 | Заказы: 3" in text
    assert "Расход: 294.00 ₽ | Себес.: 98.00 ₽" in text
    assert "пок→корз. 0.67%" in text
    assert "корз→зак. 37.50%" in text
    assert "пок→зак. 0.25%" in text


@pytest.mark.unit
def test_build_keyword_daily_history_text_sorts_newest_first() -> None:
    """Страница должна выводить дни от свежих к старым."""
    newer = KeywordDailyStat.model_validate(
        {
            "date": date(2026, 6, 16),
            "views": 10,
            "clicks": 1,
            "add_to_cart": 0,
            "orders": 0,
            "spend": 10.0,
            "cpm": 100.0,
            "avg_pos": 5.0,
        }
    )
    older = KeywordDailyStat.model_validate(
        {
            "date": date(2026, 6, 15),
            "views": 20,
            "clicks": 2,
            "add_to_cart": 1,
            "orders": 1,
            "spend": 20.0,
            "cpm": 200.0,
            "avg_pos": 7.0,
        }
    )

    text = build_keyword_daily_history_text(
        keyword_text="купить товар",
        nmids=[111, 222],
        page=1,
        total_pages=3,
        page_range=(date(2026, 6, 10), date(2026, 6, 16)),
        stats=[older, newer],
    )

    assert "История по дням (стр. 1/3)" in text
    assert "Ключ: купить товар" in text
    assert "Артикулы: 111, 222" in text
    assert text.index("16.06.2026") < text.index("15.06.2026")


@pytest.mark.unit
def test_history_keyboard_paginates_and_keeps_back_button() -> None:
    """Клавиатура должна листать страницы и возвращать в карточку ключа."""
    markup = get_keyword_daily_history_keyboard(
        keyword_setting_original_id=77,
        page=2,
        total_pages=3,
    )

    left, right = markup.inline_keyboard[0]
    parsed_left = KeywordDailyHistory.unpack(left.callback_data)
    parsed_right = KeywordDailyHistory.unpack(right.callback_data)
    assert parsed_left.keyword_setting_original_id == 77
    assert parsed_left.page == 1
    assert parsed_right.keyword_setting_original_id == 77
    assert parsed_right.page == 3

    back_button = markup.inline_keyboard[-1][0]
    parsed_back = SettingKeyword.unpack(back_button.callback_data)
    assert parsed_back.keyword_setting_original_id == 77


@pytest.mark.unit
def test_date_pagination_helpers_clamp_dates() -> None:
    """Пагинация дат должна давать предсказуемые границы страниц."""
    earliest_date = date(2026, 6, 1)
    assert (
        date_pagination.get_total_pages(
            earliest_date, page_size=7, today=date(2026, 6, 16)
        )
        == 3
    )

    page_range = date_pagination.page_to_date_range(
        2,
        page_size=7,
        earliest_date=earliest_date,
        today=date(2026, 6, 16),
    )
    assert page_range == (date(2026, 6, 3), date(2026, 6, 9))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_history_manager_returns_page_range(monkeypatch: pytest.MonkeyPatch) -> None:
    """Менеджер должен возвращать диапазон, который использовал для выборки."""
    manager = KeywordDailyHistoryManager()

    class _FixedDatetime:
        @staticmethod
        def now() -> object:
            class _Now:
                @staticmethod
                def date() -> date:
                    return date(2026, 6, 16)

            return _Now()

    monkeypatch.setattr(date_pagination, "datetime", _FixedDatetime)

    keyword_setting = MagicMock()
    keyword_setting.text = "купить товар"
    adv_setting = MagicMock()
    adv_setting.nmids = [111]
    adv_setting.adv_id = 10
    adv_setting.search_adv_id = None
    adv_setting.id = 2

    async def fake_get_earliest_date(*args, **kwargs) -> date:
        return date(2026, 6, 1)

    async def fake_load_rows(*args, **kwargs) -> list[KeywordDailyStat]:
        return []

    async def fake_get_rebound_wb_adv_ids(
        _adv_setting_id: int,
    ) -> tuple[set[int], set[int]]:
        """Unit: no live BaseRedis via get_rebound_wb_adv_ids."""
        return set(), set()

    monkeypatch.setattr(manager, "get_earliest_date", fake_get_earliest_date)
    monkeypatch.setattr(manager, "_load_history_rows", fake_load_rows)
    monkeypatch.setattr(
        "app.modules.wb_adv_updater.keyword_daily_history."
        "keyword_daily_history_manager.get_rebound_wb_adv_ids",
        fake_get_rebound_wb_adv_ids,
    )

    stats, current_page, total_pages, page_range = await manager.get_history_page(
        keyword_setting,
        adv_setting,
        page=1,
        page_size=7,
    )

    assert stats == []
    assert current_page == 1
    assert total_pages == 3
    assert page_range == (date(2026, 6, 10), date(2026, 6, 16))


@pytest.mark.asyncio
async def test_history_manager_clamps_page_when_no_nmids() -> None:
    """Без nmids менеджер не должен сохранять чужой номер страницы."""
    manager = KeywordDailyHistoryManager()

    keyword_setting = MagicMock()
    keyword_setting.text = "купить товар"
    adv_setting = MagicMock()
    adv_setting.nmids = []
    adv_setting.adv_id = 10
    adv_setting.search_adv_id = None
    adv_setting.id = 2

    stats, current_page, total_pages, page_range = await manager.get_history_page(
        keyword_setting,
        adv_setting,
        page=9,
        page_size=7,
    )

    assert stats == []
    assert current_page == 1
    assert total_pages == 1
    assert page_range is None
