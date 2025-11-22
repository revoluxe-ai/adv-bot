from collections.abc import Sequence, Callable
from collections.abc import Awaitable
from typing import cast

from sqlalchemy import select

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    single_run,
)


from app.utils.db.session_maker import get_async_session_maker as sm


class WBShopDataManager:
    def __init__(self, wb_cabinet: WBCabinet):
        self._wb_cabinet: WBCabinet = wb_cabinet
        self.shop_id: str = wb_cabinet.shop_id


    @single_run()
    async def get_calculated_keywords(self, adv: AdvSetting) -> list[CalculatedKeyword]:
        from app.modules.wb_adv_updater.phrases_processor import get_good_bad_phrases
        if not adv:
            raise RuntimeError("Сначала обновить модели")
        try:
            keywords = await get_good_bad_phrases(adv)
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

    @staticmethod
    async def __get_adv_id_to_search_adv_map(search_id_ids: set[int]) -> dict[int, AdvSetting]:
        stmt = (
            select(AdvSetting)
            .where(AdvSetting.adv_id.in_(search_id_ids))
        )
        async with sm() as session:
            result = await session.execute(stmt)
            advs: Sequence[AdvSetting] = result.scalars().all()
        adv_dict: dict[int, AdvSetting] = {adv.adv_id: adv for adv in advs}
        return adv_dict

    @single_run()
    async def get_complex_advs(self) -> list["ComplexAdv"]:
        adv_settings: list[AdvSetting] = cast(list[AdvSetting], await self.get_active_advs())
        search_adv_ids: set[int] = {adv.search_adv_id for adv in adv_settings if adv.search_adv_id}
        search_adv_idv: dict[int, AdvSetting] = await self.__get_adv_id_to_search_adv_map(search_adv_ids)
        complex_advs: list[ComplexAdv] = []
        for adv in adv_settings:
            complex_adv = ComplexAdv(
                shop_id=self.shop_id,
                adv_setting=adv,
                get_keywords_func = self.get_calculated_keywords,
                search_adv = search_adv_idv.get(adv.search_adv_id),
            )
            complex_advs.append(complex_adv)
        return complex_advs




# TODO: Реализовать гибкую модель управления через плавающую мощность и расчет потенциала от текущего статуса