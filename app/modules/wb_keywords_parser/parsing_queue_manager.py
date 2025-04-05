from collections import OrderedDict

from .parsing_found_redis_manager import  ParsingFoundRedisManager as RedisManager
from ..common_slaves.wildberries.models import WBItemPosition


class ParsingQueueManager:
    redis_manager = RedisManager()

    async def add_found_not_found_page(self,
                                       text: str,
                                       positions: list[WBItemPosition],
                                       need_nmids: set[int],
                                       page: int) -> None:
        my_positions_dict: dict[int, WBItemPosition] = {pos.nmid: pos for pos in positions if pos.nmid in need_nmids}
        for nmid in need_nmids:
            position = my_positions_dict.get(nmid)
            if position:
                await self.redis_manager.add_last_found_page_for_text_nmid(text, nmid, page)
            else:
                await self.redis_manager.add_last_not_found_page_for_text_nmid(text, nmid, page)

        return

    async def get_parsing_queue(self,
                                text: str,
                                need_nmids: set[int],
                                max_pages: int) -> list[int]:
        found_pages_all = []
        not_found_pages_all = []
        remaining_pages_all = set(range(1, max_pages + 1))

        for nmid in need_nmids:
            found_pages: list[int] = await self.redis_manager.get_found_pages_for_text_nmid(text, nmid)
            not_found_pages: list[int] = await self.redis_manager.get_not_found_pages_for_text_nmid(text, nmid)

            found_pages_all.extend(found_pages)
            not_found_pages_all.extend(not_found_pages)

            remaining_pages_all -= set(found_pages)
            remaining_pages_all -= set(not_found_pages)

        # Собираем итоговую очередь с приоритетом: найденные -> неизвестные -> не найденные
        final_queue = list(OrderedDict.fromkeys(
            found_pages_all + list(remaining_pages_all) + not_found_pages_all
        ))

        assert len(final_queue) == max_pages
        return final_queue


