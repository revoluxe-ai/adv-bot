import asyncio
import time
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_keywords_parser.parser import add_wb_positions_from_wb_search
from app.utils import redis_manager


class KeywordsParser:
    def __init__(self,  parsing_queue_dict: dict[str, set],
                 shop_id: str,
                 adv: AdvSetting,
                 keywords: list[CalculatedKeyword],
                 ):
        self._parsing_queue_dict = parsing_queue_dict
        self.__target_nmids = set(adv.nmids)
        self.__keywords = keywords
        self._adv = adv

    def create_tasks_for_keywords_parser(self, ):
        parsing_queue_dict = self._parsing_queue_dict
        nmids = self.__target_nmids
        for kw in self.__keywords:
            text = kw.text
            for nmid in nmids:
                if not text in parsing_queue_dict:
                    parsing_queue_dict[text] = set()
                parsing_queue_dict[text].add(nmid)



    async def parsing_all_keywords(self):
        parsing_queue_dict = self._parsing_queue_dict
        for kw in self.__keywords:
            text = kw.text
            need_nmids = parsing_queue_dict.pop(text, None)
            if not need_nmids:
                continue
            else:
                last_views = kw.views
                new_nmids = set()
                for nmid in new_nmids:
                    last_time_update = await redis_manager.get_last_parsing_position_time(text, nmid)
                    if last_time_update:
                        now = time.time()
                        if now - last_time_update <= 60*60:
                            continue
                        new_nmids.add(nmid)
                need_nmids = need_nmids
                if need_nmids:
                    await redis_manager.set_last_parsing_position_time(text, set(need_nmids))
                    await add_wb_positions_from_wb_search(text,
                                                         set(need_nmids),
                                                         last_views,
                                                         60)
                    await asyncio.sleep(0)










