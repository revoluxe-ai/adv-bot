from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums.auto_shelf_bid_control_strategy import \
    AutoShelfBidControlStrategy

"""DTO wrapper over AdvSetting for shop-runner control flows."""

from collections.abc import Awaitable
from dataclasses import dataclass
from typing import Protocol

from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.common_slaves.wildberries.models.bidder_mode import BidderMode
from app.modules.common_slaves.wildberries.models.enums import TargetPositionMode
from app.modules.common_slaves.wildberries.models.enums.strategy import Strategy
from app.modules.common_slaves.wildberries.models.models import BidderCoroutineType
from app.modules.common_slaves.wildberries.models.white_list_mode import WhiteListMode
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv.keyword_getting_mode import \
    KeywordGettingMode

from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatus

from app.shared.domains.wb.enums import AdvType
from app.shared.enums.wb_adv_active_status import WBAdvActiveStatus
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost




def resolve_auto_shelf_bid_control_strategy(
    raw_value: AutoShelfBidControlStrategy | str | None,
) -> AutoShelfBidControlStrategy:
    """Нормализует стратегию control-логики полок.

    None, пустые и неизвестные значения безопасно сводятся к legacy-режиму.
    """
    if raw_value is None or raw_value == "":
        return AutoShelfBidControlStrategy.PLAN_DISTANCE
    if raw_value == AutoShelfBidControlStrategy.CYCLE_METRIC:
        return AutoShelfBidControlStrategy.CPC
    if isinstance(raw_value, AutoShelfBidControlStrategy):
        return (
            AutoShelfBidControlStrategy.CPC
            if raw_value == AutoShelfBidControlStrategy.CYCLE_METRIC
            else raw_value
        )
    try:
        resolved = AutoShelfBidControlStrategy(str(raw_value))
    except ValueError:
        return AutoShelfBidControlStrategy.PLAN_DISTANCE
    if resolved == AutoShelfBidControlStrategy.CYCLE_METRIC:
        return AutoShelfBidControlStrategy.CPC
    return resolved


class GetKeywordsProvider(Protocol):
    """Провайдер keywords из Redis (``calculated_keywords:{adv_id}``), strict.

    Реализация — ``fetch_calculated_keywords_from_redis``; при miss —
    ``ShopRunnerKeywordsCacheMissError``. Пересчёт из БД — ``fetch_keywords_from_database``.

    Возврат ``Awaitable`` (не ``async def``/Coroutine): совместим с
    обёртками вроде ``@single_run``, чей тип — ``Awaitable[list[...]]``.
    """

    def __call__(
        self,
        complex_adv: ComplexAdv,
        *,
        cache_only: bool = True,
    ) -> Awaitable[list[CalculatedKeyword]]: ...


@dataclass(frozen=True, slots=True)
class TrafficClicksDTO:
    """Снимок кликов за сегодня для полочного режима (см. ``TrafficClicksManager.enrich``).

    * ``shelf_clicks`` — полки/рекомендации в авто (не по ключам).
    * ``organic_clicks`` — переходы на карточку вне суммарной рекламы комплекса.
    * ``keyword_clicks`` — клики по ключевым фразам в авто (для расчёта полок).
    """

    organic_clicks: int
    shelf_clicks: int
    keyword_clicks: int


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
        get_keywords_func: GetKeywordsProvider | None = None,
        min_nmids_bids: AdvMinNmidsBids | None = None,
        fact_pay_for_order: float | None = None,
        resolve_cpo: float | None = None,
        original_max_cpo: float | None = None,
    ):
        self._mean_auto_ctr: float | None = None
        self._shop_id = shop_id
        self._adv_setting: AdvSetting = adv_setting
        self._search_adv: AdvSetting | None = search_adv
        self._get_keywords: GetKeywordsProvider | None = get_keywords_func
        self._calculated_keywords: list[CalculatedKeyword] | None = None
        if target_pay_for_order is None:
            target_pay_for_order = resolve_target_cost(
                adv_setting.plan_for_sales_for_day,
                adv_setting.target_price_for_order,
                adv_setting.max_price_for_order,
                None,
            )
        self._target_pay_for_order = target_pay_for_order
        self._keyword_getting_mode: KeywordGettingMode = KeywordGettingMode.ALL_KEYWORDS
        self._min_nmids_bids: AdvMinNmidsBids | None = min_nmids_bids
        self._traffic_clicks_dto: TrafficClicksDTO | None = None
        self._fact_pay_for_order: float | None = fact_pay_for_order
        self._resolve_cpo: float | None = resolve_cpo
        self._original_max_cpo = original_max_cpo

    def __repr__(self):
        return str(self._adv_setting.id)

    @property
    def min_nmids_bids(self) -> AdvMinNmidsBids | None:
        """Мин. CPM auto/search по nmid; батч из get_complex_advs — один общий объект на все РК."""
        return self._min_nmids_bids

    def attach_min_nmids_bids(self, bids: AdvMinNmidsBids) -> None:
        self._min_nmids_bids = bids

    @property
    def strategy(self) -> Strategy:
        if self._adv_setting.strategy is None:
            return Strategy.MIN_CPO
        return self._adv_setting.strategy

    @property
    def auto_update_strategy(self) -> bool:
        auto_update_strategy = self._adv_setting.auto_update_strategy
        if auto_update_strategy is None:
            return True
        return auto_update_strategy


    @property
    def target_position_mode(self) -> TargetPositionMode: # для ключевых запросов
        if self._adv_setting.target_position_mode is None:
            return TargetPositionMode.MIN_CPA
        return self._adv_setting.target_position_mode

    @property
    def min_target_position(self) -> int:
        if self._adv_setting.min_target_position is None:
            return 300
        return self._adv_setting.min_target_position

    @property
    def individual_keywords_target_place_mode(self) -> bool:
        if self._adv_setting.individual_keywords_target_place_mode is None:
            return False
        return self._adv_setting.individual_keywords_target_place_mode

    @property
    def white_list_mode(self) -> WhiteListMode:
        if not self._adv_setting.white_list_mode:
            return WhiteListMode.ABOVE_MIN_RATING
        return self._adv_setting.white_list_mode

    @property
    def updater_common_bid_in_search_adv_active_status(self)-> bool:
        return self._adv_setting.updater_common_bid_in_search_adv_active_status


    @property
    def adv_setting_original_id(self) -> int:
        return self._adv_setting.id

    @property
    def bidder_for_auto(self) -> bool:
        return self._adv_setting.bidder_for_auto


    @property
    def  search_cpm(self) -> int | None:
        if self._search_adv is None:
            return None
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
                    f"Аукционная кампания не зарегистрирована для adv_id={self.auto_adv_id}"
                )
            return auction_adv_id
        raise ValueError(
            f"Неизвестный тип кампании {adv_type}"
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
        self._keyword_getting_mode = value

    @property
    def target_pay_for_order(self) -> float | None:
        return self._target_pay_for_order

    @property
    def auto_update_white_list(self) -> bool:
        return self._adv_setting.auto_update_white_list

    @property
    def auto_update_minus_phrases(self) -> bool:
        """Возвращает persisted-флаг без постоянного ``None → True`` fallback."""
        return bool(getattr(self._adv_setting, "auto_update_minus_phrases", False))

    @property
    def bidder_active(self) -> bool:
        return bool(self._adv_setting.bidder_active)

    @property
    def bidder_coroutine_type(self) -> BidderCoroutineType:
        return self._adv_setting.bidder_coroutine_type

    @property
    def bid_cpm_step(self) -> int:
        return self._adv_setting.bidder_step



    @property
    def all_adv_ids(self) -> set[int]:
        adv_ids: set[int] = set()
        if self._adv_setting.adv_id:
           adv_ids.add(self._adv_setting.adv_id)
        if self._search_adv:
            adv_ids.add(self._search_adv.adv_id)
        return adv_ids

    @property
    def hard_min_ctr(self) -> int | None:
        raw = self._adv_setting.hard_min_ctr
        if raw is None:
            return None
        return int(raw)

    @property
    def original_adv_setting_id(self) -> int:
        return self._adv_setting.id


    @property
    def auto_adv_id(self) -> int:
        return self._adv_setting.adv_id

    @property
    def rec_system_promotion_mode_active(self) -> bool:
        """Режим «Полки» в настройках РК (``AdvSetting.rec_system_mode``)."""
        return self._adv_setting.rec_system_mode

    @property
    def auto_shelf_bid_control_enabled(self) -> bool:
        """Флаг включения control-контура общей ставки полок."""
        return bool(self._adv_setting.auto_shelf_bid_control_enabled)

    @property
    def auto_shelf_bid_control_strategy(self) -> AutoShelfBidControlStrategy:
        """Стратегия выбора main bid для auto_shelf_bid_control."""
        return resolve_auto_shelf_bid_control_strategy(
            getattr(self._adv_setting, "auto_shelf_bid_control_strategy", None)
        )

    @property
    def traffic_clicks_dto(self) -> TrafficClicksDTO | None:
        """Клики орг/пол за сегодня; None если полки выкл или enrich не вызывали / упал."""
        if not self.rec_system_promotion_mode_active:
            return None
        return self._traffic_clicks_dto

    @traffic_clicks_dto.setter
    def traffic_clicks_dto(self, value: TrafficClicksDTO | None) -> None:
        if not self.rec_system_promotion_mode_active:
            self._traffic_clicks_dto = None
            return
        self._traffic_clicks_dto = value

    @property
    def is_shelf_activation_allowed(self) -> bool:
        """``shelf_clicks > organic_clicks``. Смысл — ``auto_updater_traffic_policy``."""
        dto = self.traffic_clicks_dto
        if dto is None:
            return False
        return dto.shelf_clicks > dto.organic_clicks

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
    def shelf_promotion_active(self) -> bool:
        """rec_system (полки) + авто-кампания started — как во v2 для полочной фазы."""
        return self.rec_system_promotion_mode_active and self.auto_adv_active_status

    @property
    def v3_rollout_aggressiveness(self) -> int:
        return int(self._adv_setting.aggressiveness)

    @property
    def card_ab_hold_mode(self) -> str:
        """Durable A/B Hold mode (spec ``card-ab-hold-mode``): off/pending_setup/active."""
        raw = getattr(self._adv_setting, "card_ab_hold_mode", None)
        if raw is None:
            return "off"
        return str(raw)

    @property
    def card_ab_hold_phase(self) -> str | None:
        """Durable A/B Hold epoch phase; ``None`` = legacy MVP-1 (phase IS NULL).

        Используется Auto bid freeze (FINDING-PBH-003): post-confirm phases
        ``pending_intent`` / ``wb_sync`` / ``ready_active`` при ``pending_setup``.
        """
        raw = getattr(self._adv_setting, "card_ab_hold_phase", None)
        if raw is None:
            return None
        text = str(raw).strip()
        return text or None

    @property
    def keyword_calibration_max_step(self) -> int:
        return int(self._adv_setting.keyword_calibration_max_step)

    @property
    def shop_id(self) -> str:
        return self._shop_id or ""

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
    def auto_updater_version(self) -> int | None:
        return self._adv_setting.automatic_version

    @property
    def is_part_auto_setting_active(self) -> bool:
        adv = self._adv_setting
        individual_keywords_mode_active = bool(
            adv.individual_keywords_target_place_mode
        )
        ver = (
            self.auto_updater_version
            if self.auto_updater_version is not None
            else 2
        )
        if ver in (1, 2, 3):
            return any(
                [
                    adv.auto_update_white_list,
                    adv.auto_update_target_place,
                    individual_keywords_mode_active,
                ]
            )
        raise RuntimeError("Not Implemented for this version")

    @property
    def adv_setting(self) -> AdvSetting:
        return self._adv_setting

    @property
    def auto_update_setting_version(self) -> int | None:
        return self._adv_setting.automatic_version

    def _filter_keywords(
        self, keywords: list[CalculatedKeyword]
    ) -> list[CalculatedKeyword]:
        if self.keyword_getting_mode == KeywordGettingMode.ONLY_ACTIVE_KEYWORDS:
            return [kw for kw in keywords if kw.status == KeywordStatus.GOOD]
        return keywords

    async def get_keywords(
        self, *, cache_only: bool = True
    ) -> list[CalculatedKeyword]:
        """Keywords только из Redis (прогрев — snapshot updater).

        Args:
            cache_only: должен быть ``True``; пересчёт из БД в shop-runner запрещён.

        Raises:
            ShopRunnerKeywordsCacheMissError: hash в Redis отсутствует.

        Непустой ответ кэшируется на инстансе; пустой ``[]`` (маркер ``__empty__``)
        при каждом вызове перечитывается из Redis, чтобы подхватить warmup.

        Для UI / ручного пересчёта — ``fetch_keywords_from_database`` (``keywords_access``).
        """
        if not self._get_keywords:
            raise RuntimeError("_get_keywords not set")
        if not cache_only:
            raise RuntimeError(
                "get_keywords(cache_only=False) отключён в shop-runner: "
                "используйте fetch_keywords_from_database() для пересчёта из БД "
                "или дождитесь snapshot warmup."
            )
        if self._calculated_keywords is not None:
            return self._filter_keywords(self._calculated_keywords)

        cached = await self._get_keywords(self)
        # Пустой [] (__empty__ в Redis) не кэшируем на инстансе: snapshot warmup
        # может записать keywords после первого чтения.
        if cached:
            self._calculated_keywords = cached
        return self._filter_keywords(cached)

    @property
    def exponet_predict_ctr(self) -> float:
        return self._adv_setting.exponent_predict_ctr

    @property
    def target_place(self) -> int:
        place = self._adv_setting.max_place
        return 0 if place is None else int(place)

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
        """Флаг автобюджета: free top-up и paid start/pause (см. auto_budget_watchdog)."""
        return bool(self._adv_setting.auto_budget_watchdog_enabled)

    @property
    def use_common_budget(self) -> bool:
        return bool(self._adv_setting.use_common_budget)

    @property
    def common_budget_daily_limit(self) -> int | None:
        return self._adv_setting.common_budget_daily_limit

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
        return bool(self._adv_setting.bidder_active)

    @property
    def max_user_cpm(self) -> int:
        cpm = self._adv_setting.max_cpm
        return 0 if cpm is None else int(cpm)

    @property
    def fact_pay_for_order(self) -> float | None:
        """Фактическое CPO кампании (cost per order) из plan-fact статистики."""
        return self._fact_pay_for_order

    @property
    def resolve_cpo(self) -> float | None:
        """Resolve CPO кампании (целевое/разрешенное значение CPO)."""
        return self._resolve_cpo

    @property
    def original_max_cpo(self) -> float | None:
        """Исходный max CPO из настроек РК до синтетических пересчётов бюджета."""
        return self._original_max_cpo
