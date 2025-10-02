import bootstrap
from sqlalchemy import select

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet

SHOP_IDS = [
    '28cfff92-285b-488d-9d90-f9e177071a24',
    'd0343ade-8ecf-43b6-8c1b-18795df41eec'

]

nmids = [
225396267,
225399426,
258133864,
258134277,
258075751,
213732128,
213474172,
228848863,
224454964,
225399421,
189457897,
213474166,
224279979,
258038055,
227086898,
224475289,
228848388,
258087408,
224554826,
213221416,
225083367,
234761314,
221996034,
221996061,
234762016,
234756930,
234761343,
234760459,
234756675,
234754504,
234762437,
234761302,
234757783,
234754827,
234758477,
234762023,
234757877]

async def activate_advs():
    from app.utils.db.session_maker import get_async_session_maker as sm
    stmt = select(AdvSetting).join(WBCabinet).where(
        WBCabinet.shop_id.in_(SHOP_IDS))
    async with sm() as session:
        advs: list[AdvSetting] = (await session.execute(stmt)).scalars().all()
        advs = [adv for adv in advs if adv.search_adv_id]
        advs = [adv for adv in advs if adv.active_status != 'done']
        advs = [adv for adv in advs if set(adv.nmids) <= set(nmids)]
        advs = [adv for adv in advs if '<!-' in adv.name]
        for adv in advs:
            adv.bot_active = True
        await session.commit()



if __name__ == "__main__":

    import asyncio

    asyncio.run(activate_advs())

