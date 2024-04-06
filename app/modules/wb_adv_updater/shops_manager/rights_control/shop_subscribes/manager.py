from sqlalchemy import select
from app.utils.db.models import User
from app.modules.common_slaves.wildberries.models import WBCabinet
from app.utils.db.session_maker import get_async_session_maker
from . import messages

_sm = get_async_session_maker()

#период в сутках - сообщение
messages_period = [
    1, messages.TestPeriodExpire,
    2, messages.TestPeriodExpire,
    3, messages.TestPeriodExpire,

]



async def check_shop_subscribes():
    async with _sm() as session:
        stmt = select(WBCabinet).filter(WBCabinet.expiration_time >)
        result = await session.execute(stmt)
        shop_subscribes = result.scalars().all()
    return shop_subscribes








async def check_all():
    return None