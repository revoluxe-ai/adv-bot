from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCard, WBCategory
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm


class AdvParameterManager:
    async def get_min_cpm(self, adv: AdvSetting) -> int:
        nmid = adv.nmids[0]

        stmt = (
            select(WBCategory.wb_category_name)
            .join(WBCategory.wb_cards)
            .where(WBCard.nmid == nmid)
        )
        async with sm() as session:
            result = await session.execute(stmt)
            wb_category_name = result.scalar_one()

        min_cpm = await redis_manager.get_min_cpm_by_category_name(wb_category_name)
        if not min_cpm:
            return 150
        return min_cpm
