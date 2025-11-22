import logging
import random
from collections import OrderedDict


# TODO Более тщательно продумать логику задержек при парсинге
from app.modules.common_slaves.wildberries.models import WBItemPosition
from app.modules.wb_keywords_parser.parsing_found_redis_manager import (
    ParsingFoundRedisManager,
)
from app.modules.wb_keywords_parser.wb_parser.parsing_queue_mode import ParsingQueueMode
from app.settings import settings

logger = logging.getLogger(__name__)


class ParsingQueueManager:
    def __init__(self):
        self.redis_manager = ParsingFoundRedisManager()

    async def add_found_not_found_page(
        self,
        text: str,
        positions: list[WBItemPosition],
        need_nmids: set[int],
        page: int,
    ) -> None:
        my_positions_dict: dict[int, WBItemPosition] = {
            pos.nmid: pos for pos in positions if pos.nmid in need_nmids
        }
        for nmid in need_nmids:
            position = my_positions_dict.get(nmid)
            if position:
                await self.redis_manager.add_last_found_page_for_text_nmid(
                    text, nmid, page
                )
            else:
                await self.redis_manager.add_last_not_found_page_for_text_nmid(
                    text, nmid, page
                )

        return

    async def get_parsing_queue(
        self, text: str, need_nmids: set[int], max_pages: int
    ) -> list[int]:
        found_pages_all = []
        not_found_pages_all = []
        remaining_pages_all = set(range(1, max_pages + 1))
        if settings.PARSING_QUEUE_MODE == ParsingQueueMode.SIMPLE_QUEUE:
            return list(range(1, max_pages + 1))
        for nmid in need_nmids:
            found_pages: list[int] = (
                await self.redis_manager.get_found_pages_for_text_nmid(text, nmid)
            )
            not_found_pages: list[int] = (
                await self.redis_manager.get_not_found_pages_for_text_nmid(text, nmid)
            )

            found_pages_all.extend(found_pages)
            not_found_pages_all.extend(not_found_pages)

            remaining_pages_all -= set(found_pages)
            remaining_pages_all -= set(not_found_pages)

        # Преобразуем множество в список только после завершения цикла
        remaining_pages_all = list(remaining_pages_all)
        random.shuffle(remaining_pages_all)

        # Собираем итоговую очередь с приоритетом: найденные -> неизвестные -> не найденные
        final_queue = list(
            OrderedDict.fromkeys(
                found_pages_all + remaining_pages_all + not_found_pages_all
            )
        )

        # Проверяем, что все страницы присутствуют
        if len(final_queue) != max_pages:
            logger.warning(
                f"Количество страниц в очереди ({len(final_queue)}) не соответствует ожидаемому ({max_pages})"
            )
            # Добавляем недостающие страницы
            all_pages = set(range(1, max_pages + 1))
            missing_pages = list(all_pages - set(final_queue))
            final_queue.extend(missing_pages)

        return final_queue
