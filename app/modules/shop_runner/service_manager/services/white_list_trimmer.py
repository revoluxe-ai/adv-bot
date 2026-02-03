from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.utils.db.session_maker import get_async_session_maker as sm
from tests.factories import HardStatus
import logging


logger = logging.getLogger(__name__)

class WhiteListTrimmer:

    async def trim(self, complex_adv: ComplexAdv) -> None:
        keywords = await complex_adv.get_keywords()
        top_key_in_auto_position: int | None = self._get_top_key_in_auto_position(keywords)
        if top_key_in_auto_position is None:
            return None
        keywords_below = keywords[top_key_in_auto_position:]
        candidates_to_auto_ids: list[int] = []
        for kw in keywords_below:
            if kw.hard_status == HardStatus.WHITELIST:
                candidates_to_auto_ids.append(kw.keyword_setting_original_id)
        stmt = update(KeywordSetting)\
        .where(KeywordSetting.id.in_(candidates_to_auto_ids))\
        .values(hard_status=1)
        async with sm(read_only=False) as session:
           await session.execute(stmt)
           await session.commit()
        return None

    @staticmethod
    def _get_top_key_in_auto_position(keywords: list[CalculatedKeyword]) -> int | None:
         for n, kw in enumerate(keywords):
             if kw.hard_status == HardStatus.IN_TEST:
                 return n
         else:
             return None


