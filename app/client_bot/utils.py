from __future__ import annotations

import csv
import logging
from datetime import datetime
from io import StringIO
from typing import TYPE_CHECKING

from sqlalchemy import select, Result
from sqlalchemy.ext.asyncio import AsyncSession

from app.client_bot.const import AUTO_MODE, BLACK_LIST, TURN_OFF, WHITE_LIST

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker

if TYPE_CHECKING:
    from app.core.redis_manager_v2.redis_client import RedisClient

logger = logging.getLogger(__name__)


_sm = get_async_session_maker


# @dataclass
# class KeywordForKeyboard:
#     text: str
#     good: bool
#     statistic: CalculatedKeyword
#     keyword_settings: KeywordSetting
#     adv_setting: AdvSetting
#     turn_on: bool
#     bad_reason: str | None = None


async def get_keywords_for_keyboard(adv_setting: AdvSetting) -> list[CalculatedKeyword]:
    # Получаем shop_id через join с WBCabinet
    stmt = select(WBCabinet.shop_id).join(WBCabinet.adv_settings)\
    .where(AdvSetting.id == adv_setting.id)

    async with _sm(read_only=True) as session:
        result = await session.execute(stmt)
        shop_id = result.scalar_one()

    search_adv = None  # Инициализация
    search_adv_id = adv_setting.search_adv_id
    if search_adv_id:
        stmt = select(AdvSetting).where(AdvSetting.adv_id == search_adv_id)
        async with _sm(read_only=True) as session:
            result: Result = await session.execute(stmt)
            search_adv = result.scalar_one_or_none()
    complex_adv = ComplexAdv(
        shop_id=shop_id,
        adv_setting=adv_setting,
        search_adv=search_adv,
    )
    all_phrases: list[CalculatedKeyword] = await get_good_bad_phrases(complex_adv)
    return all_phrases


async def get_csv_file(adv_setting: AdvSetting) -> str:
    keywords: list[CalculatedKeyword] = await get_keywords_for_keyboard(adv_setting)
    csv_output = StringIO()
    csv_writer = csv.writer(
        csv_output,
        delimiter=";",
        quotechar='"',
        quoting=csv.QUOTE_MINIMAL,
        lineterminator="\n",
    )
    header_row = [
        "Запрос(вхождение)",
        "Запрос(точное соответствие)",
        "Клики",
        "Просмотры",
        "Показов (история)",
        "CTR",
        "Прогнозируемый CTR",
        "Включен-Выключен",
        "Статус",
        "Позиция",
        "Рейтинг ключа",
        "Заказов",
    ]
    data_rows: list[list[str]] = []
    # Заголовки столбцов

    for keyword in keywords:
        clicks = keyword.clicks
        assert clicks is not None
        views = keyword.views
        assert views is not None
        predicted_ctr = keyword.predict_ctr or keyword.ctr
        ctr = round(keyword.ctr * 100, 2)
        try:
            keyword_reason = keyword.reason
        except Exception:
            keyword_reason = None
        if keyword_reason == "max_position":
            hard_status = "ЦП"
        elif keyword.hard_status == BLACK_LIST:
            hard_status = "НРФ"
        elif keyword_reason == "max_cpc":
            hard_status = "МС"
        elif keyword.hard_status == TURN_OFF:
            hard_status = "О"
        elif keyword.hard_status == WHITE_LIST:
            hard_status = "БС"
        elif keyword.hard_status == AUTO_MODE:
            hard_status = "А"
        else:
            raise ValueError(f"Unknown hard_status: {keyword.hard_status}")

        turn_on = "✅Включен" if keyword.status == KeywordStatus.GOOD else "❌Выключен"
        # TODO: Привести выгрузку к текущему формату, по уму - полностью переделать, убрать не а
        # Определение позиции (единое поле)
        position_value = keyword.position
        if position_value > 0:
            first_position = int(position_value + 0.5)
        elif position_value == 0:
            first_position = ">"
        else:
            first_position = "?"  # TODO: Кажется тут ошибка, потому что если позиция не может быть None
        data_rows.append(
            [
                keyword.text,
                '"' + keyword.text + '"',
                str(clicks),
                str(views),
                str(keyword.total_views if keyword.total_views else 0),
                str(ctr).replace(".", ","),
                str(round(predicted_ctr * 100, 2)).replace(".", ","),
                turn_on,
                hard_status,
                str(first_position),
                str(round(keyword.rating_by_orders * 100, 4)).replace(".", ","),
                str(keyword.total_orders if keyword.total_orders else 0),
            ]
        )

    data_rows.sort(key=lambda loc_row: int(loc_row[-1]), reverse=True)
    rows = [header_row] + data_rows

    for row in rows:
        logger.debug(row)
        csv_writer.writerow(row)
    csv_string = csv_output.getvalue()
    csv_output.close()

    return csv_string


async def create_user(
    session: AsyncSession,
    user_telegram_id: int,
    *,
    username: str | None = None,
    adv_updater_user_chat_id: int | None = None,
) -> User:
    """Создаёт пользователя в БД и возвращает его. Сессия должна быть с read_only=False."""
    user = User(
        user_telegram_id=user_telegram_id,
        username=username,
        adv_updater_user_chat_id=adv_updater_user_chat_id,
        wb_tokens=[],
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def build_cpm_date_map(
    adv_setting: AdvSetting,
    keywords: list[CalculatedKeyword],
    redis_client: "RedisClient",
) -> dict[str, tuple[float | None, datetime | None]]:
    """
    Build map text -> (cpm, date) for list display.
    Priority: 1) set bid (Redis), 2) bid_decision_log, 3) Redis calculated_keywords cache, 4) keyword.cpm/timestamp.
    """
    from app.modules.keyword_bid_from_log import get_latest_keyword_bids
    from app.modules.calculated_keywords_redis_cache_manager.redis_manager import (
        RedisCalculatedKeywordsCacheManager,
    )

    texts = [kw.text for kw in keywords]
    result: dict[str, tuple[float | None, datetime | None]] = {}
    search_adv_id = getattr(adv_setting, "search_adv_id", None)
    nmids = list(adv_setting.nmids or [])

    # 1) Set bid from Redis
    from app.modules.cluster_bids_redis import get_set_bid_map

    set_bid_map = await get_set_bid_map(
        search_adv_id, nmids, texts, adv_setting, redis_client
    )

    # 2) bid_decision_log (one call for all texts)
    bid_log_map: dict[str, tuple[float, datetime]] = {}
    if search_adv_id is not None and nmids and texts:
        bid_log_map = await get_latest_keyword_bids(search_adv_id, nmids, texts)

    # 3) Redis calculated_keywords cache
    cache_map: dict[str, CalculatedKeyword] = {}
    if texts:
        cache_mgr = RedisCalculatedKeywordsCacheManager()
        cache_map = await cache_mgr.get_calculated_keywords_map(adv_setting.adv_id, texts)

    text_to_kw = {kw.text: kw for kw in keywords}

    for text in texts:
        if text in set_bid_map:
            cpm, dt = set_bid_map[text]
            result[text] = (cpm, dt)
        elif text in bid_log_map:
            cpm_curr, decision_time = bid_log_map[text]
            result[text] = (cpm_curr, decision_time)
        elif text in cache_map:
            kw = cache_map[text]
            result[text] = (kw.cpm, kw.timestamp)
        elif text in text_to_kw:
            kw = text_to_kw[text]
            result[text] = (kw.cpm, kw.timestamp)
        else:
            result[text] = (None, None)

    return result
