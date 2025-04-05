import asyncio
import datetime

from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.wb_adv_updater import data_manager
import logging

from app.modules.wb_keywords_parser.parsing_task import ParsingTask
from app.utils import redis_manager

logger = logging.getLogger(__name__)

class ParserTasksGenerator:
    def __init__(self, adv: AdvSetting):
        self._adv = adv


    async def generator(self):
        keywords = await data_manager.get_good_bad_phrases(self._adv)
        nmid = self._adv.nmids[0]
        for keyword in keywords:
            if keyword.hard_status == 2:
                continue
            text = keyword.text
            last_position = await redis_manager.get_keyword_position(text, nmid)
            if last_position and last_position.timestamp < datetime.datetime.now() - datetime.timedelta(hours=1)\
                    or not last_position:
                task = ParsingTask(keyword.text,
                                   nmid=nmid,
                                   adv_id_order=self._adv.adv_id)
                yield task







