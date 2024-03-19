from sqlalchemy.orm import selectinload
from app.modules.common_slaves.wildberries.models import WBUserCabinet, WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from sqlalchemy import select
from app.utils.db.models import User
import logging

sm = get_async_session_maker()

logger = logging.getLogger(__name__)






@staticmethod
async def get_super_wb_user_cabinets():
    all_super_wb_user_cabinets = []
    async with sm() as session:
        query = select(WBCabinet).options(selectinload(WBCabinet.wb_user_cabinets)\
                                             .selectinload(WBUserCabinet.user)\
                                              .selectinload(User.wb_tokens))

        wb_cabinets = await session.execute(query)
        wb_cabinets = wb_cabinets.scalars().all()
        for  wb_cabinet in wb_cabinets:
            super_user = User()
            shop_id = wb_cabinet.shop_id
            tokens_for_shop = set()
            wb_user_cabinets = wb_cabinet.wb_user_cabinets
            for wb_user_cabinet in wb_user_cabinets:
                user = wb_user_cabinet.user
                [tokens_for_shop.add(token) for token in user.wb_tokens if token.shop_id == shop_id]
            super_user.wb_tokens = list(tokens_for_shop)
            super_wb_user_cabinet = WBUserCabinet()
            super_wb_user_cabinet.id = wb_cabinet.id
            super_wb_user_cabinet.user = super_user
            super_wb_user_cabinet.wb_cabinet = wb_cabinet
            all_super_wb_user_cabinets.append(super_wb_user_cabinet)
    return all_super_wb_user_cabinets


