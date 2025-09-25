from asyncio import Future

from app.core.utils.future_getter_base import FutureGetterBase
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import WBItemPosition, AdvSetting
from app.modules.wb_keywords_parser.wb_parser import parser
from app.utils.redis_manager import get_keyword_position


class CurrentPositionsForAdvGetter(FutureGetterBase):
    async def _fetch(self,
                     adv: AdvSetting,
                     best_keyword_future: Future[CalculatedKeyword]) -> dict[int, int | None]:
        # Получаем nmids и ключевое слово из adv
        nmids = adv.nmids
        if not nmids:
            return {}  # Если нет nmids, возвращаем пустой словарь
        best_keyword: CalculatedKeyword = await best_keyword_future
        text = best_keyword.text
        await parser.add_wb_positions(text, set(nmids), delay=0.1)
        # Получаем позиции из Redis
        result = {}
        for nmid in nmids:
            wb_position: WBItemPosition | None = await get_keyword_position(text, nmid)
            result[nmid] = wb_position.position if wb_position else None
        return result

    def get_future(self, adv: AdvSetting, best_keyword_future: Future[CalculatedKeyword]) -> Future:
        return super()._get_future(adv, best_keyword_future)
