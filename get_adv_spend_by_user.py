import datetime

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, WBUserCabinet, WBCabinet, AdvKeyword, WBToken
from app.modules.wb_adv_updater.data_managers import get_keyword_statistic
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker, get_session_maker
from collections import defaultdict


aio_sm = get_async_session_maker()
sm = get_session_maker()

dd = defaultdict(float)

def get_adv_spend_by_user():
    from sqlalchemy import func
    with sm() as session:
        stmt = (
            select(User.username, func.sum(AdvKeyword.spend).label('total_spend'))
            # .options(selectinload(User.wb_tokens))
            .join(User.wb_user_cabinets)
            .join(WBUserCabinet.wb_cabinet)
            .join(WBCabinet.adv_settings)
            .join(AdvSetting.adv_keywords)


            .where(and_(
                # User.wb_tokens.any(WBToken.active == True),
                AdvSetting.bot_active == True,
                WBCabinet.active == True,
                AdvSetting.active_status == 'started',

                AdvKeyword.date == datetime.datetime.now().date()
            ))
            .group_by(User.username).order_by(func.sum(AdvKeyword.spend).desc())
        )
        result = session.execute(stmt)  # Используйте execute для выполнения запроса
        counter = 0
        for row in result:
            stmt = select(WBToken).join(WBToken.user)\
                .where(and_(User.username == row.username, WBToken.active == True))
            result = session.execute(stmt)
            tokens = result.scalar()
            if tokens:
                counter += 1
                print(f" {counter} Username: https://t.me/{row.username}, Total Spend: {row.total_spend}")











if __name__ == '__main__':
    get_adv_spend_by_user()
