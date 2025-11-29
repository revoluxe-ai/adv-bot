from collections.abc import Callable, Awaitable, Sequence

from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from app.modules.common_slaves.wildberries.models import AdvSetting


class _CPMs:
    def __init__(self, adv_setting: AdvSetting, search_adv: AdvSetting | None):
        self._auto_cpm = adv_setting.cpm
        self._search_cpm = search_adv.cpm if search_adv else None

    @property
    def auto_cpm(self) -> int:
        return self._auto_cpm

    @property
    def search_cpm(self) -> int:
        return self._search_cpm


class ComplexAdv:
    def __init__(
        self,
        shop_id: str,
        adv_setting: AdvSetting,
        search_adv: AdvSetting | None,
        get_keywords_func: Callable[[...], Awaitable[list[CalculatedKeyword]]],
    ):

        self._mean_auto_ctr: float | None = None
        self._shop_id = shop_id
        self._adv_setting: AdvSetting = adv_setting
        self._search_adv: AdvSetting | None = search_adv
        self._get_keywords = get_keywords_func
        self._calculated_keywords: list[CalculatedKeyword] | None = None


    @property
    def auto_adv_id(self) -> int:
        return self._adv_setting.adv_id

    @property
    def rec_system_promotion_mode_active(self) -> bool:
        return self._adv_setting.rec_system_mode

    async def get_mean_auto_ctr(self) -> float | None:
        from app.modules.wb_adv_updater.min_ctr_manager.min_ctr_manager import (
            MinCtrManager,
        )

        if self._mean_auto_ctr is None:
            min_ctr_manager = MinCtrManager(self._adv_setting)
            mean_auto_ctr = await min_ctr_manager.get_mean_ctr_auto_adv()
            self._mean_auto_ctr = mean_auto_ctr
        return self._mean_auto_ctr

    @property
    def search_adv_active_status(self) -> bool:
        if self._search_adv and self._search_adv.active_status == "started":
            return True
        return False

    @property
    def shop_id(self) -> str:
        return self._shop_id

    @property
    def search_adv(self):
        return self._search_adv

    def nmids(self) -> Sequence[int]:
        return self._adv_setting.nmids

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
            return any(
                [
                    adv.auto_update_white_list,
                    adv.auto_update_target_place,
                    adv.auto_update_exponent,
                ]
            )
        else:
            raise RuntimeError("Not Implemented for this version")

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
        cpms = _CPMs(self._adv_setting, self._search_adv)
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
