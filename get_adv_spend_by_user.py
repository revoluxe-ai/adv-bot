import datetime
from collections import defaultdict

from sqlalchemy import and_, select

from app.modules.common_slaves.wildberries.models import (
    AdvKeyword,
    AdvSetting,
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.models import User
from app.utils.db.session_maker import get_async_session_maker, get_session_maker # type: ignore[attr-defined]

aio_sm = get_async_session_maker()
sm = get_async_session_maker()  # type: ignore[attr-defined]

dd = defaultdict(float)


def get_adv_spend_by_user():
    from sqlalchemy import func

    with sm() as session:  # type: ignore[attr-defined]
        stmt = (
            select(User.username, func.sum(AdvKeyword.spend).label("total_spend"))
            # .options(selectinload(User.wb_tokens))
            .join(User.wb_user_cabinets)
            .join(WBUserCabinet.wb_cabinet)
            .join(WBCabinet.adv_settings)
            .join(AdvSetting.adv_keywords)
            .where(
                and_(
                    # User.wb_tokens.any(WBToken.active == True),
                    AdvSetting.bot_active.is_(True),
                    WBCabinet.active.is_(True),
                    AdvSetting.active_status == "started",
                    AdvKeyword.date == datetime.datetime.now().date(),
                )
            )
            .group_by(User.username)
            .order_by(func.sum(AdvKeyword.spend).desc())
        )
        result = session.execute(stmt)  # Используйте execute для выполнения запроса
        counter = 0
        for row in result:
            stmt = (
                select(WBToken)
                .join(WBToken.user)
                .where(and_(User.username == row.username, WBToken.active.is_(True)))
            )
            result = session.execute(stmt)
            tokens = result.scalar()
            if tokens:
                counter += 1
                print(
                    f" {counter} Username: https://t.me/{row.username}, Total Spend: {row.total_spend}"
                )


if __name__ == "__main__":
    get_adv_spend_by_user()
