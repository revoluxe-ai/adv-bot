from typing import Sequence

from sqlalchemy import update

from app.modules.common_slaves.wildberries.models import KeywordSetting
import typing
if typing.TYPE_CHECKING:
    from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import ComplexAdv
from app.utils.db.session_maker import get_async_session_maker as sm

async def delete_keywords_from_wl_by_mean_auto_ctr(complex_adv: 'ComplexAdv') -> None:
    keywords = await complex_adv.get_keywords()
    mean_auto_ctr: float = await complex_adv.get_mean_auto_ctr()

    keyword_ids_in_wh_least_mean_ctr: Sequence[int] = \
        [kw.keyword_setting_original_id for kw in keywords if kw.predict_ctr <= mean_auto_ctr and kw.hard_status == 2]
    if not keyword_ids_in_wh_least_mean_ctr:
        return None
    async with sm(read_only=False) as session:
        stmt = update(KeywordSetting)\
        .where(KeywordSetting.id.in_(keyword_ids_in_wh_least_mean_ctr))\
            .values({'hard_status':1})
        await session.execute(stmt)
        await session.commit()

    return None