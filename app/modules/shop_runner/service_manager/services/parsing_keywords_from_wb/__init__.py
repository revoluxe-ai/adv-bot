"""Парсинг ключевых слов для рекламных кампаний Wildberries."""

import logging
from collections.abc import AsyncGenerator, Awaitable
from datetime import datetime, timedelta

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
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
    adv_id = int(adv.adv_id)

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
                raise RuntimeError("position не может быть None здесь")
            position_ = ps.position
            if position_ != -1:
                positions_in_index.append(position_)
        limit = max([len(positions_in_index), 1])
        return limit

    parsing_limit: int = get_parsing_limit()
    for keyword in sorted_keywords[:parsing_limit]:
        text = keyword.text
        nmid = keyword.nmid
        views_now = keyword.views or 0
        position = keyword.position  # позиция: int | None | 0 | -1
        last_update: datetime | None = keyword.position_update

        last_views = await redis_manager.get_last_views(adv_id, text)
        should_parse = False

        # если нет сохранённых просмотров — сохраняем и парсим
        if last_views is None:
            await redis_manager.set_last_views(adv_id, text, views_now)
            should_parse = True

        # если вообще нет просмотров (товар неактивен) — пропускаем
        elif views_now == 0:
            continue

        # если просмотры выросли существенно — парсим
        elif views_now - last_views > settings.MIN_DIFF_VIEWS_FOR_PARSING_KEYWORDS:
            should_parse = True

        # если товар "в индексе, но не на сайте" (позиция == 0), и просмотры изменились — парсим
        elif position in [-1, 0] and views_now != last_views:
            should_parse = True

        # если давно не обновлялась позиция — парсим
        elif (
                last_update
                and last_update < now - timedelta(hours=max_hours_period)
        ):
            should_parse = True

        # сохраняем новые просмотры, если решено парсить
        if should_parse:
            await redis_manager.set_last_views(adv_id, text, views_now)
            yield text, nmid
