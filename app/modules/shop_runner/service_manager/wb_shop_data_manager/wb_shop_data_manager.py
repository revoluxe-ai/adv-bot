from collections.abc import Sequence, Callable
from collections.abc import Awaitable
from typing import cast

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
        self._wb_cabinet: WBCabinet = wb_cabinet
        self.shop_id: str = wb_cabinet.shop_id

  
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


    async def __get_adv_id_to_search_adv_map(self, search_id_ids: set[int]) -> dict[int, AdvSetting]:
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
                adv_setting=adv,
                get_keywords_func = self.get_calculated_keywords,
                search_adv = search_adv_idv.get(adv.search_adv_id),
            )
            complex_advs.append(complex_adv)
        return complex_advs



class _CPMs:
    def __init__(self, adv_setting: AdvSetting,
                 search_adv: AdvSetting | None):
        self.auto_cpm = adv_setting.cpm
        self.search_cpm = search_adv.cpm if search_adv else None


class ComplexAdv:
    def __init__(
        self,
        adv_setting: AdvSetting,
        search_adv: AdvSetting | None,
        get_keywords_func: Callable[[...], Awaitable[list[CalculatedKeyword]]],
    ):
        self._adv_setting: AdvSetting = adv_setting
        self._search_adv: AdvSetting | None = search_adv
        self._get_keywords = get_keywords_func
        self._calculated_keywords: list[CalculatedKeyword] | None = None

    @property
    def is_target_position_control_enabled(self) -> bool:
        return self._adv_setting.auto_update_target_place

    @property
    def is_white_list_control_enabled(self) -> bool:
        return self._adv_setting.auto_update_white_list

    @property
    def is_exponent_control_enabled(self) -> bool:
        return self._adv_setting.auto_update_exponent


    @property
    def auto_updater_version(self) -> int:
        return self._adv_setting.automatic_version

    @property
    def is_part_auto_setting_active(self) -> bool:
        adv = self._adv_setting
        if self.auto_updater_version == 1:
            return adv.auto_update_white_list or adv.auto_update_target_place
        elif self.auto_updater_version == 2:
            return any([
                adv.auto_update_white_list,
                adv.auto_update_target_place,
                adv.auto_update_exponent
            ])
        else:
            raise RuntimeError('Not Implemented for this version')


    @property
    def adv_setting(self) -> AdvSetting:
        return self._adv_setting

    @property
    def auto_update_setting_version(self) -> int:
        return self._adv_setting.automatic_version
    

    async def get_keywords(self) -> list[CalculatedKeyword]:
        if not self._calculated_keywords:
            self._calculated_keywords = await self._get_keywords(self._adv_setting)
        return self._calculated_keywords


    @property    
    def exponet_predict_ctr(self) -> float:
        return self._adv_setting.exponent_predict_ctr


    @property
    def target_place(self) -> int:
        return self._adv_setting.max_place

    @property 
    def exponent_predict_ctr(self) -> float:
        return self._adv_setting.exponent_predict_ctr
    
    @property
    def db_id(self) -> int:
        return self._adv_setting.id


    @property
    def adv_id(self) -> int:
        return self._adv_setting.adv_id

    @property
    def auto_add_only_relevant_phrase(self):
        return self._adv_setting.auto_add_only_relevant_phrase

    @property
    def current_cpms(self) -> _CPMs:
        cpms = _CPMs(self._adv_setting,
                     self._search_adv)
        return cpms

    @property
    def is_bidder_for_auto_cpm_active(self) -> bool:
        return self._adv_setting.bidder_for_auto


    @property
    def is_bidder_for_search_adv_active(self) -> bool:
        return self._adv_setting.bidder_active

    @property
    def max_user_cpm(self) -> int:
        return self._adv_setting.max_cpm


# TODO: Реализовать гибкую модель управления через плавающую мощность и расчет потенциала от текущего статуса