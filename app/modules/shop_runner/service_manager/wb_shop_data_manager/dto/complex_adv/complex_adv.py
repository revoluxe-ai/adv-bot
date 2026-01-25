from collections.abc import Callable, Awaitable


from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.bidder_mode import BidderMode
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.keyword_getting_mode import \
    KeywordGettingMode

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus
import typing

from app.shared.domains.wb.enums import AdvType
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus

if typing.TYPE_CHECKING:
    from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword

class _CPMs:
    def __init__(self, adv_setting: AdvSetting, search_adv: AdvSetting | None):
        self._auto_cpm = adv_setting.cpm
        self._search_cpm = search_adv.cpm if search_adv else None

    @property
    def auto_cpm(self) -> int:
        return self._auto_cpm

    @property
    def search_cpm(self) -> int | None:
        return self._search_cpm


class ComplexAdv:
    def __init__(
        self,
        adv_setting: AdvSetting,
        search_adv: AdvSetting | None = None,
        target_pay_for_order: float | None = None,
        shop_id: str | None = None,
        get_keywords_func: Callable[[...], Awaitable[list["CalculatedKeyword"]]] | None = None,
    ):
        self._mean_auto_ctr: float | None = None
        self._shop_id = shop_id
        self._adv_setting: AdvSetting = adv_setting
        self._search_adv: AdvSetting | None = search_adv
        self._get_keywords = get_keywords_func
        self._calculated_keywords: list["CalculatedKeyword"] | None = None
        self._target_pay_for_order: float | None = target_pay_for_order
        self._keyword_getting_mode: KeywordGettingMode = KeywordGettingMode.ALL_KEYWORDS
    @property
    def bidder_for_auto(self) -> bool:
        return self._adv_setting.bidder_for_auto


    @property
    def  search_cpm(self) -> int | None:
        return self._search_adv.cpm

    @property
    def search_adv_active_status_str(self) -> WBAdvActiveStatus | None:
        if self._search_adv is None:
            return None
        return WBAdvActiveStatus(self._search_adv.active_status)

    @property
    def auto_adv_active_status_str(self) -> WBAdvActiveStatus:
        return WBAdvActiveStatus(self._adv_setting.active_status)

    @property
    def bot_active(self) -> bool:
        return self._adv_setting.bot_active


    @property
    def auction_adv_id(self) -> int | None:
        if self._search_adv is None:
            return None
        else:
            return  self._search_adv.adv_id

    def get_adv_id_by_type(self, adv_type: AdvType) -> int:
        if adv_type == AdvType.AUTO:
            return self.auto_adv_id
        if adv_type == AdvType.SEARCH:
            auction_adv_id = self.auction_adv_id
            if auction_adv_id is None:
                raise ValueError(
                    "Аукционная кампания не зарегистрирована для adv_id=%s"
                    % self.auto_adv_id
                )
            return auction_adv_id
        raise ValueError(
            "Неизвестный тип кампании %s" % adv_type
        )

    @property
    def bidder_mode(self) -> BidderMode:
        if self._adv_setting.bidder_mode is None:
            return BidderMode.BY_POSITIONS
        return self._adv_setting.bidder_mode


    @property
    def keyword_getting_mode(self) -> KeywordGettingMode:
        return self._keyword_getting_mode

    @keyword_getting_mode.setter
    def keyword_getting_mode(self, value: KeywordGettingMode):
        if not isinstance(value, KeywordGettingMode):
            raise ValueError()
        self._keyword_getting_mode = value

    @property
    def target_pay_for_order(self) -> float | None:
        return self._target_pay_for_order

    @property
    def auto_update_white_list(self) -> bool:
        if self._adv_setting.auto_update_white_list is None:
            return True
        return self._adv_setting.auto_update_white_list


    @property
    def bidder_active(self) -> bool:
        return self._adv_setting.bidder_active

    @property
    def bidder_coroutine_type(self) -> BidderCoroutineType:
        return self._adv_setting.bidder_coroutine_type

    @property
    def bid_cpm_step(self) -> int:
        return self._adv_setting.bidder_step



    @property
    def all_adv_ids(self) -> set[int]:
        adv_ids: set[int] = set()
        adv_ids.add(self._adv_setting.adv_id)
        if self._search_adv:
            adv_ids.add(self._search_adv.adv_id)
        return adv_ids

    @property
    def hard_min_ctr(self) -> int | None:
        return self._adv_setting.hard_min_ctr

    @property
    def original_adv_setting_id(self) -> int:
        return self._adv_setting.id


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
    def auto_adv_active_status(self) -> bool:
        if self._adv_setting.active_status == "started":
            return True
        return False


    @property
    def shop_id(self) -> str:
        return self._shop_id

    @property
    def search_adv(self) -> AdvSetting | None:
        return self._search_adv

    @property
    def nmids(self) -> list[int]:
        nmids = list(self._adv_setting.nmids)
        nmids.sort()
        return nmids

    @property
    def main_nmid(self) -> int:
        return self.nmids[0]

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

    async def get_keywords(self) -> list["CalculatedKeyword"]:
        if not self._calculated_keywords:
            if not self._get_keywords:
                raise RuntimeError("_get_keywords not set")
            self._calculated_keywords = await self._get_keywords(self)
        if self.keyword_getting_mode == KeywordGettingMode.ONLY_ACTIVE_KEYWORDS:
            keywords = [kw for kw in self._calculated_keywords if kw.status == KeywordStatus.GOOD]
        else:
            keywords = self._calculated_keywords
        return keywords

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
    def auto_budget_daily_limit(self) -> int:
        return self._adv_setting.auto_budget_daily_limit

    @property
    def search_auto_budget_daily_limit(self) -> int:
        return self._adv_setting.search_auto_budget_daily_limit

    @property
    def auto_budget_watchdog_enabled(self) -> bool:
        return bool(self._adv_setting.auto_budget_watchdog_enabled)

    @property
    def search_adv_id(self) -> int | None:
        return self._adv_setting.search_adv_id

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
