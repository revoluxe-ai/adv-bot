from typing import Sequence

from sqlalchemy import select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    single_run,
)
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm


class WBShopDataManager:
    def __init__(self, wb_cabinet: WBCabinet):
        self._wb_cabinet = wb_cabinet
        self.shop_id = wb_cabinet.shop_id

    @single_run()
    async def get_calculated_keywords(self, adv: AdvSetting) -> list[CalculatedKeyword]:
        if not adv:
            raise RuntimeError("Сначала обновить модели")
        try:
            keywords = await data_manager.get_good_bad_phrases(adv)
        except Exception as exc:
            raise exc

        return keywords

    @single_run()
    async def get_active_advs(self) -> list[AdvSetting]:
        shop_id = self.shop_id
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .filter(WBCabinet.shop_id == shop_id, AdvSetting.bot_active)
        )
        async with sm() as session:
            result = await session.execute(stmt)
            advs: Sequence[AdvSetting] = result.scalars().all()
        adv_settings_list = list(advs)
        if not adv_settings_list:
            raise NotFoundActiveAdvCompany("Нет активных кампаний")
        return adv_settings_list
