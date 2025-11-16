from collections.abc import Callable, Awaitable

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting


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
    def main_nmid(self) -> int:
        return self._adv_setting.nmids[0]


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
