from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.wb_api.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import KeywordSetting, AdvSetting, WBCard
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.white_list_updater.backend.excs import NotEnoughKeywordsError
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm

class WhiteListUpdater:
    async def update_white_list(self, keywords: list[CalculatedKeyword], min_all_keywords: int):
        if len([keyword for keyword in keywords if keyword.predict_ctr is not None]) < min_all_keywords:
             raise NotEnoughKeywordsError(f'Not enough keywords for white list update. ')
        assert [isinstance(keyword, CalculatedKeyword) for keyword in keywords]
        keywords.sort(key=lambda kw: kw.rating_by_predict_ctr, reverse=True)
        top_keyword: CalculatedKeyword = keywords[0]
        stmt = select(KeywordSetting)\
        .options(selectinload(KeywordSetting.adv_setting))\
            .where(KeywordSetting.id == top_keyword.keyword_setting.id)
        async with sm(read_only=False) as session:
            result = await session.execute(stmt)
            keyword_setting: KeywordSetting = result.scalar()
            keyword_setting.hard_status = 2
            adv_setting: AdvSetting = keyword_setting.adv_setting
            adv_setting.hard_min_ctr = None
            adv_setting.bidder_active = True
            await session.commit()
        return top_keyword

    async def update_max_bid(self, adv_setting: AdvSetting, best_keyword: CalculatedKeyword):
        text = best_keyword.text
        max_bet  = await redis_manager.get_max_bet(text)
        if not max_bet:
            max_bet = 500
        async with sm(read_only=False) as session:
            stmt = select(AdvSetting)\
            .filter(AdvSetting.id == adv_setting.id)
            result = await session.execute(stmt)
            adv_setting = result.scalar()
            adv_setting.bidder_active = True
            adv_setting.max_cpm = max_bet
            await session.commit()


