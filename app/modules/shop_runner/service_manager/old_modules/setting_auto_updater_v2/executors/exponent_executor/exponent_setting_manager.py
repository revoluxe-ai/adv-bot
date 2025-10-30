from sqlalchemy import update

from app.core.wb_api.data_classes import adv
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting
from ._get_next_raise_exponent import get_next_raise_exponent
from ._get_next_down_exponent import get_next_down_exponent
from app.utils.db.session_maker import get_async_session_maker as sm


async def raise_exponent_and_update_leader_to_white_list(adv: AdvSetting, keywords: list[CalculatedKeyword]) -> bool: # уменьшает продажи и расход
    exponent_now = adv.exponent_predict_ctr
    new_exponent = get_next_raise_exponent(exponent_now, keywords)
    if not new_exponent:
        touch_down = True
        return touch_down
    async with sm(read_only=False) as session:
        stmt = update(AdvSetting).where(
            AdvSetting.adv_id == adv.adv_id
        ).values(exponent_predict_ctr=new_exponent)
        await session.execute(stmt)
        await session.commit()
    return False



async def down_exponent_and_update_leader_to_white_list(adv: AdvSetting, keywords: list[CalculatedKeyword]) -> bool: # увеличивает продажи и расход
    exponent_now = adv.exponent_predict_ctr
    new_exponent = get_next_down_exponent(exponent_now, keywords)
    if not new_exponent:
        touch_down = True
        return touch_down
    async with sm(read_only=False) as session:
        stmt = update(AdvSetting).where(
            AdvSetting.adv_id == adv.adv_id
        ).values(exponent_predict_ctr=new_exponent)
        await session.execute(stmt)
        await session.commit()
    return False




