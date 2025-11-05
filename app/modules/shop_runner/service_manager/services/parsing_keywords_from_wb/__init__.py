"""Парсинг ключевых слов для рекламных кампаний Wildberries."""

import logging
from collections.abc import AsyncGenerator, Awaitable
from datetime import datetime, timedelta

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.settings import settings
from app.utils import redis_manager

logger = logging.getLogger(__name__)


async def parsing_keywords_for_adv_generator(
    adv: AdvSetting, keywords: Awaitable[list[CalculatedKeyword]]
) -> AsyncGenerator[tuple[str, int], None]:
    """Генератор для получения ключевых слов, которые нужно парсить для рекламной кампании.

    Args:
        adv:
        keywords:

    Returns:

    """
    keywords_result = await keywords
    if not keywords_result:
        logger.error(f"Нет ключевых для кампании {adv.adv_id}")
        return
    nmid = int(adv.nmids[0])
    adv_id = int(adv.adv_id)

    # Разделим на ключи с позициями и без
    last_positions: dict[str, WBItemPosition] = {}
    keywords_with_positions: list[CalculatedKeyword] = []
    keywords_without_positions: list[CalculatedKeyword] = []

    for keyword in keywords_result:
        position = keyword.position
        if position is not None:
            keywords_with_positions.append(keyword)
        else:
            keywords_without_positions.append(keyword)

    # Сначала те без позиции, потом с позицией
    sorted_keywords = keywords_without_positions + keywords_with_positions

    max_hours_period = settings.MAX_HOURS_PERIOD_FOR_PARSING_KEYWORDS
    now = datetime.now()

    def get_parsing_limit() -> int:
        """Лимит на количество ключевых слов для парсинга за один заход."""
        positions_in_index = []
        for ps in keywords_with_positions:
            if ps.position is None:
                raise  RuntimeError("position не может быть None здесь")
            position_ = ps.position
            if position_ != -1:
                positions_in_index.append(position_)
        limit = max([len(positions_in_index), 1])
        return limit

    parsing_limit: int = get_parsing_limit()
    for keyword in sorted_keywords[:parsing_limit]:
        text = keyword.text
        views_now = keyword.views
        last_position = last_positions.get(text)
        last_views = await redis_manager.get_last_views(adv_id, text)
        should_parse = False
        if last_views is None:
            last_views = views_now
        if not last_position:
            await redis_manager.set_last_views(adv_id, text, views_now)
            should_parse = True          
        elif views_now == 0:
            continue
        elif views_now - last_views > settings.MIN_DIFF_VIEWS_FOR_PARSING_KEYWORDS:
            should_parse = True
        elif last_position.position == 0 and (views_now != last_views):
            should_parse = True
        elif last_position and last_position.timestamp \
            and last_position.timestamp < now - timedelta(hours=max_hours_period):
            should_parse = True
        if should_parse:
            await redis_manager.set_last_views(adv_id, text, views_now)
            yield text, nmid
    return
