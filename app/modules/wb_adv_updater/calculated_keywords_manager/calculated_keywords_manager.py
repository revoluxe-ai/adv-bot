"""Расчёт и кэширование keyword-состояния для WB adv updater.

Модуль собирает данные ClickHouse/Redis/WB manager hub для расчёта ставок,
диагностик и bidder-status. Fallback создания WBManagerHub оставлен только для
нештатных путей и логируется warning-ом для обнаружения утечки отдельного pool.
"""

from __future__ import annotations
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import inspect
import logging
from numbers import Real
from typing import Generator, Protocol, Sequence, TypeVar, cast
from typing_extensions import ParamSpec

from sqlalchemy import select


from dependency_injector import providers
from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from .dto.keyword_hard_status import KeywordHardStatus
from .dto.states import KeywordStatus, KeywordStatusReason
from .enum import KeywordRatingMode
from .keyword_stat import KeywordStat, make_zero_keyword_stat
from app.core.clickhouse_manager import BaseClickHouseManager
from app.core.clikhouse_client_manager import  get_clickhouse_client
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.redis_keyword_bidder_status_manager import (
    RedisKeywordBidderStatusManager,
)
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager import (
    WBManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_cooldown_entry import (
    AboveTargetCooldownEntry,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.above_target_min_bid_cooldown import (
    apply_above_target_min_bid_cooldown,
    max_search_min_bid_for_complex_nmids,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.orders_per_1000_rub import (
    calc_pay_for_order,
)
from app.shared.domains.wb.utils.cost_resolver import resolve_target_cost
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.pre_calculated_keyword import PreCalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.inner_dto.keyword_cpm_sources import KeywordCpmSources
from app.modules.wb_adv_updater.calculated_keywords_manager.redis_above_target_min_bid_cooldown_manager import (
    RedisAboveTargetMinBidCooldownManager,
)
from ...calculated_keywords_redis_cache_manager.redis_manager import RedisCalculatedKeywordsCacheManager
from ...common_slaves.wildberries.models import KeywordSetting
from app.utils.db.session_maker import  get_async_session_maker as sm
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from operator import  attrgetter

logger = logging.getLogger(__name__)



import typing

from ...common_slaves.wildberries.models.enums.strategy import Strategy
from ...common_slaves.wildberries.models.white_list_mode import WhiteListMode


if typing.TYPE_CHECKING:
    from app.core.di.wb_manager_hub.wb_manager_hub import WBManagerHub
    from app.modules.cpm_sources_resolver.dto import AllCpmSourcesPerText
    from ...shop_runner.service_manager.wb_shop_data_manager import ComplexAdv


P = ParamSpec("P")
R = TypeVar("R")


class _AsyncDecoratorFactory(Protocol): # pyright: ignore
    def __call__(
        self, *, ttl: str, lock: bool
    ) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
        ...


class _ClickHouseNamedResultsResponse(Protocol):
    def named_results(self) -> Generator[dict[str, int | float | str], None, None]:
        ...



# TODO: Нужно сделать автоматизацию по проверке обновлений API и внесением правок через ИИ


def _coerce_optional_int_for_resolve(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Real):
        return int(float(value))
    return None


def _coerce_optional_float_for_resolve(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Real):
        return float(value)
    return None


def _can_override_target_cost_from_ch(
    *,
    plan_orders: int | None,
    target_pay_for_order: float | None,
    max_pay_for_order: float | None,
    fact_predict_orders: float | None,
) -> bool:
    """Whether CH fact has enough signal to override the safe fallback target cost.

    ``complex_adv.target_pay_for_order`` is the safe fallback. ClickHouse-derived
    resolve may overwrite it only when all inputs required by ``resolve_target_cost``
    are present. In particular, ``fact_predict_orders=None`` must not be treated as
    ``0`` here, otherwise an incomplete CH row would incorrectly force ``max``.
    """
    return (
        plan_orders is not None
        and target_pay_for_order is not None
        and max_pay_for_order is not None
        and fact_predict_orders is not None
    )


class CalculatedKeywordsManager(BaseClickHouseManager):
    async def get_calculated_keywords(
        self,
        complex_adv: "ComplexAdv",
        min_days: int = 7,
        min_views: int = 500,
        *,
        adv_trace: object | None = None,
    ) -> list[CalculatedKeyword]:
        # TODO: Сделать на будущее более глобальные объекты для списков, в котором будут передаваться не только данные, но и метаданные
        # TODO: тут получаем только для одного артикула, возможно, что нал

        stats = await self._get_all_stats(complex_adv, min_days, min_views)

        from app.modules.keywords_manager.keywords_manager import KeywordsManager
        keyword_manager = KeywordsManager()
        await keyword_manager.create_new_keyword_settings(complex_adv, stats)
        keyword_hard_statuses = await self._get_all_keyword_setting(complex_adv)
        pre_calculated_keywords = self.__create_pre_calculated_keywords(
            keyword_hard_statuses,
            stats,
            complex_adv,
        )
        if not pre_calculated_keywords:
            return []
        from app.modules.cpm_sources_resolver import CpmSourcesResolver

        texts = [s.text for s in stats]
        all_sources_by_text = await CpmSourcesResolver.get_all_sources(
            complex_adv, texts
        )
        pre_calculated_keywords = self.__enrich_pre_calculated_with_cpm_sources(
            pre_calculated_keywords, all_sources_by_text
        )
        now = datetime.now(UTC)
        min_bid_for_adv = max_search_min_bid_for_complex_nmids(
            list(complex_adv.nmids), complex_adv.min_nmids_bids
        )
        if min_bid_for_adv is None:
            min_bid_for_adv = await self._fetch_min_search_bid_aggregate(complex_adv)

        cooldown_map: dict[str, AboveTargetCooldownEntry | None] | None = None
        cooldown_updates: dict[str, AboveTargetCooldownEntry | None] | None = None
        cooldown_redis_mgr: RedisAboveTargetMinBidCooldownManager | None = None
        if min_bid_for_adv is not None:
            cooldown_updates = {}
            hub_kw = await self._get_wb_manager_hub(complex_adv)
            cooldown_redis_mgr = RedisAboveTargetMinBidCooldownManager(
                hub_kw.redis_client_wrapper
            )
            pre_texts = [p.keyword_setting.text for p in pre_calculated_keywords]
            cooldown_map = await cooldown_redis_mgr.get_many(
                complex_adv.adv_id, pre_texts
            )

        calculated_keyword_list = await self.__get_calculated_keywords(
            complex_adv,
            pre_calculated_keywords,
            min_bid_for_adv=min_bid_for_adv,
            cooldown_map=cooldown_map,
            cooldown_updates=cooldown_updates,
            now=now,
        )
        if cooldown_redis_mgr is not None and cooldown_updates:
            await cooldown_redis_mgr.apply_updates(
                complex_adv.adv_id, cooldown_updates
            )
        await self._set_calculated_keywords_in_redis_cache(
            complex_adv, calculated_keyword_list
        )
        return calculated_keyword_list

    async def _get_all_stats(
        self, complex_adv: 'ComplexAdv', min_days: int, min_views: int
    ) -> list[KeywordStat]:
        nmids = complex_adv.nmids
        return await self._get_keywords_stat_from_clickhouse(nmids, min_days, min_views)

    @staticmethod
    def __enrich_pre_calculated_with_cpm_sources(
        pre_keywords: list[PreCalculatedKeyword],
        all_sources_by_text: dict[str, "AllCpmSourcesPerText"],
    ) -> list[PreCalculatedKeyword]:
        """Fill KeywordCpmSources from all four sources: set_bid, api, bid_log from resolver; stats from cluster_stat."""
        enriched: list[PreCalculatedKeyword] = []
        for pre_kw in pre_keywords:
            text = pre_kw.keyword_setting.text
            sources_row = all_sources_by_text.get(text)
            cpm_from_stats = pre_kw.cluster_stat.cpm
            if sources_row is not None:
                sources = KeywordCpmSources(
                    cpm_set_bid=sources_row.cpm_set_bid,
                    cpm_set_bid_date=sources_row.cpm_set_bid_date,
                    cpm_from_api=sources_row.cpm_from_api,
                    cpm_from_bid_log=sources_row.cpm_from_bid_log,
                    cpm_from_bid_log_date=sources_row.cpm_from_bid_log_date,
                    cpm_from_stats=cpm_from_stats,
                    cpm_from_stats_date=None,
                )
            else:
                sources = KeywordCpmSources(
                    cpm_set_bid=None,
                    cpm_set_bid_date=None,
                    cpm_from_api=None,
                    cpm_from_bid_log=None,
                    cpm_from_bid_log_date=None,
                    cpm_from_stats=cpm_from_stats,
                    cpm_from_stats_date=None,
                )
            enriched.append(
                PreCalculatedKeyword(
                    adv_id=pre_kw.adv_id,
                    keyword_setting=pre_kw.keyword_setting,
                    cluster_stat=pre_kw.cluster_stat,
                    bidder_status=pre_kw.bidder_status,
                    rating_mode=pre_kw.rating_mode,
                    cpm_sources=sources,
                )
            )
        return enriched

    async def _get_keywords_stat_from_clickhouse(self,
                                                  nmids: list[int],
                                                  min_days: int,
                                                  min_views: int,
                                                  cart_to_order_window:int=14
                                                  ) -> list[KeywordStat]:
        """Fetch keyword statistics from ClickHouse and parse them into models.

        This is a higher-level wrapper around
        ``__get_keywords_stat_from_clickhouse``. It forwards the query
        parameters to the cached low-level ClickHouse call and converts the
        raw dictionaries returned from ClickHouse into ``KeywordStat`` model
        instances.

        Args:
            nmids: List of Wildberries product IDs (nmids) to fetch statistics
                for. A list is used so that statistics for multiple products
                can be retrieved in a single ClickHouse query.
            min_days: Minimum number of days of statistics that must be
                available for a keyword to be included in the result.
            min_views: Minimum number of views required for a keyword to be
                included in the result set.
            cart_to_order_window: Number of days to use as the conversion
                window when aggregating cart-to-order statistics.

        Returns:
            A list of ``KeywordStat`` objects with aggregated statistics for
            the requested nmids that satisfy the specified filters.

        Note:
            This method itself is not cached. Caching is applied at the level
            of ``__get_keywords_stat_from_clickhouse``, which is decorated
            with ``@noself(cache)`` and caches the raw ClickHouse query
            results for a short period.
        """
        result: list[dict[str, int | float | str]] = await self.__get_keywords_stat_from_clickhouse(
            nmids, min_days, min_views, cart_to_order_window
        )
        stats: list[KeywordStat] = []
        for obj in result:
            stat = KeywordStat.model_validate(obj)
            stats.append(stat)
        return stats

    async def __get_keywords_stat_from_clickhouse(self,
                                                  nmids: list[int],
                                                  min_days: int,
                                                  min_views: int,
                                                  cart_to_order_window:int=14
                                                  ) -> list[dict[str, int | float | str]]:
        query = self._get_query('get_clusters_stats')

        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                response = await client.query(
                    query,
                    parameters={
                        "nmids": nmids,
                        "min_views": min_views,
                        "min_days": min_days,
                        "conv_days": cart_to_order_window,
                    },
                )

        typed_response = cast(_ClickHouseNamedResultsResponse, response)
        result: Generator[dict[str, int | float | str], None, None] = typed_response.named_results()
        return list(result)



    @staticmethod
    def resolve_keyword_rating_mode(complex_adv: "ComplexAdv") -> KeywordRatingMode:
        """Режим рейтинга для сортировки ключей; V3 всегда MIN_CPO."""
        if complex_adv.bot_active:
            return KeywordRatingMode.BY_MIN_CPO
        if complex_adv.strategy == Strategy.MIN_CPO:
            return KeywordRatingMode.BY_MIN_CPO
        if complex_adv.strategy == Strategy.MAX_CONV:
            return KeywordRatingMode.BY_MAX_CONV
        raise ValueError(f"Not implemented strategy: {complex_adv.strategy}")

    @staticmethod
    def __create_pre_calculated_keywords(keyword_hard_statuses: list[KeywordHardStatus],
                                               stats: list[KeywordStat],
                                               complex_adv: 'ComplexAdv') \
            -> list[PreCalculatedKeyword]:
        from .convertor import  keyword_setting_to_keyword_setting_dto
        text_to_stat = {stat.text: stat for stat in stats}

        rating_mode = CalculatedKeywordsManager.resolve_keyword_rating_mode(complex_adv)

        keywords: list[PreCalculatedKeyword] = []
        for keyword_hard_status in keyword_hard_statuses:
            keyword_setting = keyword_hard_status.keyword_setting
            stat = text_to_stat.get(keyword_setting.text)
            if not stat:
                stat = make_zero_keyword_stat(keyword_setting.text)
            keyword_setting_dto = keyword_setting_to_keyword_setting_dto(keyword_setting)
            calculated_keyword = PreCalculatedKeyword(
                keyword_setting=keyword_setting_dto,
                cluster_stat=stat,
                adv_id=complex_adv.adv_id,
                rating_mode=rating_mode,
                bidder_status=keyword_hard_status.bidder_keyword_status,
            )
            keywords.append(calculated_keyword)
        return keywords

    async def _get_all_keyword_setting(self, complex_adv: 'ComplexAdv') -> list[KeywordHardStatus]:
        adv_setting_original_id = complex_adv.original_adv_setting_id

        stmt = select(KeywordSetting).where(KeywordSetting.adv_setting_id == adv_setting_original_id)
        async with sm(read_only=True) as session:
            result = await session.execute(stmt)
            keyword_settings: Sequence[KeywordSetting] = result.scalars().all()

        texts: list[str] = [kw.text for kw in keyword_settings]
        keyword_hard_statuses_map = await self._get_bidder_keyword_statuses(complex_adv, texts)
        keyword_hard_statuses: list[KeywordHardStatus] = []
        for keyword_setting in keyword_settings:
            keyword_hard_statuses.append(KeywordHardStatus(
                keyword_setting=keyword_setting,
                bidder_keyword_status=keyword_hard_statuses_map[keyword_setting.text]
            ))
        return keyword_hard_statuses

    @staticmethod
    async def __get_calculated_keywords(
        complex_adv: "ComplexAdv",
        pre_keywords: list[PreCalculatedKeyword],
        *,
        min_bid_for_adv: int | None = None,
        cooldown_map: dict[str, AboveTargetCooldownEntry | None] | None = None,
        cooldown_updates: dict[str, AboveTargetCooldownEntry | None] | None = None,
        now: datetime | None = None,
    ) -> list[CalculatedKeyword]:
        calculated_keyword_list: list[CalculatedKeyword] = []
        from .dto.inner_dto.keyword_state import KeywordState
        from app.shared.domains.wb.utils.auto_campaign_cost_activity import (
            is_auto_campaign_active,
        )
        pre_keywords.sort(key=lambda kw: kw.rating or 0, reverse=True)
        _plan_o = _coerce_optional_int_for_resolve(
            complex_adv.adv_setting.plan_for_sales_for_day
        )
        _plan_t = _coerce_optional_float_for_resolve(
            complex_adv.adv_setting.target_price_for_order
        )
        _plan_m = _coerce_optional_float_for_resolve(
            complex_adv.adv_setting.max_price_for_order
        )

        # Target cost already resolved at WBShopDataManager.get_complex_advs():
        # PreComplexAdv.resolved_target_pay_for_order uses batch get_latest_plan_facts.
        # Do not query ClickHouse again per campaign.
        resolved_target_cost: float | None
        _raw_target = complex_adv.target_pay_for_order
        if _raw_target is None or isinstance(_raw_target, bool):
            resolved_target_cost = None
        elif isinstance(_raw_target, Real):
            resolved_target_cost = float(_raw_target)
        else:
            resolved_target_cost = None
        if resolved_target_cost is None:
            resolved_target_cost = resolve_target_cost(
                _plan_o, _plan_t, _plan_m, None
            )
        _resolved_ch: float | None = None
        try:
            _summary = await PlanFactReader().get_latest_plan_fact(
                complex_adv.adv_id
            )
            if _summary is not None and _can_override_target_cost_from_ch(
                plan_orders=_plan_o,
                target_pay_for_order=_plan_t,
                max_pay_for_order=_plan_m,
                fact_predict_orders=_summary.fact_predict_orders,
            ):
                _resolved_ch = resolve_target_cost(
                    _plan_o, _plan_t, _plan_m, _summary.fact_predict_orders
                )
        except Exception:
            logger.exception(
                "PlanFactReader.get_latest_plan_fact failed for adv_id=%r; "
                "falling back to target_pay_for_order / plan without CH fact",
                getattr(complex_adv, "adv_id", None),
            )
            _resolved_ch = None

        if _resolved_ch is not None:
            resolved_target_cost = _resolved_ch

        auto_campaign_active: bool | None = None
        rec_conversion: float | None = None
        # TODO: Тут надо внимательно перепроверить логику с rec_conversion, сделать тесты, делаю коммит авансом
        if complex_adv.rec_system_promotion_mode_active:
            from app.modules.shop_runner.wb_stat_manager.rec_conversion_service import (
                get_rec_conversion,
            )
            # TODO: Придумать фоллбек для этой функции
            auto_campaign_active = await is_auto_campaign_active(complex_adv.adv_setting)
            if auto_campaign_active is not None:
                rec_conversion = await get_rec_conversion(complex_adv.adv_id)

        def _above_rec_conversion(pre_kw_: PreCalculatedKeyword) -> bool | None:
            """conv(ключ) > rec_conversion (полки). Зачем — ``auto_updater_traffic_policy``."""
            if auto_campaign_active is False:
                return None  # правило не применяем
            if not complex_adv.rec_system_promotion_mode_active or rec_conversion is None:
                return None
            return pre_kw_.cluster_stat.conv_views_to_orders > rec_conversion

        def _apply_above_target_cooldown(
            pre_kw_: PreCalculatedKeyword, state_: KeywordState
        ) -> KeywordState:
            keyword_pay_for_order = calc_pay_for_order(pre_kw_.orders_per_1000_rub)
            return apply_above_target_min_bid_cooldown(
                pre_kw=pre_kw_,
                base_state=state_,
                min_bid_for_adv=min_bid_for_adv,
                keyword_pay_for_order=keyword_pay_for_order,
                resolved_target_cost=resolved_target_cost,
                cooldown_map=cooldown_map,
                cooldown_updates=cooldown_updates,
                now=now,
            )

        white_list = [kw for kw in pre_keywords
                                        if kw.hard_status in [2]]
        if not white_list:
            best_keyword = max(pre_keywords, key=attrgetter("rating"))
            for pre_kw in pre_keywords:
                if pre_kw.hard_status == 4:
                    state = KeywordState(
                        status=KeywordStatus.GOOD,
                        reason=KeywordStatusReason.ALWAYS_ON,
                        best_keyword_status=pre_kw == best_keyword,
                    )
                else:
                    state = KeywordState(
                        status=KeywordStatus.BAD,
                        reason=KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS,
                        best_keyword_status=False,
                    )
                state = _apply_above_target_cooldown(pre_kw, state)
                calculated_keyword = CalculatedKeyword(
                    adv_id=pre_kw.adv_id,
                    keyword_setting=pre_kw.keyword_setting,
                    cluster_stat=pre_kw.cluster_stat,
                    state=state,
                    target_pay_for_order=complex_adv.target_pay_for_order,
                    above_rec_conversion=None,
                    cpm_sources=pre_kw.cpm_sources,
                    rating=pre_kw.rating,
                )
                calculated_keyword_list.append(calculated_keyword)
            return calculated_keyword_list


        best_keyword = max(pre_keywords, key=lambda kw: kw.rating or 0)
        white_list_without_non_views = [kw for kw in white_list if kw.cluster_stat.views > 0]
        if not white_list_without_non_views:
            rating_of_worst_keyword = None
        else:
            worst_keyword = min(white_list_without_non_views, key=lambda kw: kw.rating)
            rating_of_worst_keyword = worst_keyword.rating
        for pre_kw in pre_keywords:
            best_keyword_status = True if pre_kw == best_keyword else False
            hard_status = pre_kw.hard_status
            above_rec = _above_rec_conversion(pre_kw)
            if hard_status == 4:
                status = KeywordStatus.GOOD
                reason = KeywordStatusReason.ALWAYS_ON
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status,
                )

            elif complex_adv.auto_add_only_relevant_phrase and not pre_kw.relevant:
                state = KeywordState(
                    status=KeywordStatus.BAD,
                    reason=KeywordStatusReason.NOT_RELEVANT_PHRASE,
                    best_keyword_status=best_keyword_status,
                )

            elif hard_status == 3:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.TURN_OFF
                best_keyword_status = True if pre_kw==best_keyword else False
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif hard_status == 2:
                status = KeywordStatus.GOOD
                reason = KeywordStatusReason.WHITE_LIST
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif  rating_of_worst_keyword is None:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.NOT_FOUND_WHITE_LIST_KEYWORD_WITH_RATING
                state  = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status,
                )
            elif hard_status == 0:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.BLACK_LIST
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status
                )
            elif complex_adv.white_list_mode == WhiteListMode.ABOVE_MIN_RATING and \
                    pre_kw.rating >= rating_of_worst_keyword:
                if above_rec is False:
                    status = KeywordStatus.BAD
                    reason = KeywordStatusReason.BELOW_REC_CONVERSION
                else:
                    status = KeywordStatus.GOOD
                    reason = KeywordStatusReason.MORE_THEN_RATING_BY_ORDERS
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status,
                )
            else:
                status = KeywordStatus.BAD
                reason = KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS
                state = KeywordState(
                    status=status,
                    reason=reason,
                    best_keyword_status=best_keyword_status,
                )

            state = _apply_above_target_cooldown(pre_kw, state)
            calculated_keyword_list.append(
                CalculatedKeyword(
                    adv_id=pre_kw.adv_id,
                    keyword_setting=pre_kw.keyword_setting,
                    cluster_stat=pre_kw.cluster_stat,
                    state=state,
                    target_pay_for_order=complex_adv.target_pay_for_order,
                    above_rec_conversion=above_rec,
                    cpm_sources=pre_kw.cpm_sources,
                    rating=pre_kw.rating,
                )
            )
        return calculated_keyword_list

    async def _fetch_min_search_bid_aggregate(self, complex_adv: "ComplexAdv") -> int | None:
        """Мин. search CPM из Redis v2 через ``WBManager.read_min_bids_cache_only`` (без WB API).

        При cache miss — WARNING в логах (см. ``wb_manager``), не исключение; агрегат может
        быть ``None`` до догрузки ``preload_min_bids_cache_miss`` / snapshot.
        """
        nmids = list(complex_adv.nmids)
        if not nmids:
            return None
        hub = await self._get_wb_manager_hub(complex_adv)
        min_bids = await WBManager.read_min_bids_cache_only(
            [complex_adv],
            hub.redis_client_wrapper,
            shop_id=complex_adv.shop_id or "",
            context=f"calculated_keywords adv_id={complex_adv.adv_id}",
        )
        return max_search_min_bid_for_complex_nmids(nmids, min_bids)

    @staticmethod
    async def resolve_wb_manager_hub(complex_adv: "ComplexAdv") -> "WBManagerHub":
        """Публичный доступ к WBManagerHub (snapshot warmup и внешние caller'ы)."""
        return await CalculatedKeywordsManager._get_wb_manager_hub(complex_adv)

    @staticmethod
    async def _get_wb_manager_hub(complex_adv: "ComplexAdv") -> "WBManagerHub":
        from app.core.di.wb_manager_hub import WBManagerHubFactory

        try:
            return WBManagerHubFactory.get_wb_manager_from_context()
        except RuntimeError:
            from app.core.di.client_di.wb_manager_hub_container import WBManagerHubContainer
            from app.core.mp.wb.api.httpx_client_handler import HttpxClientHandler
            from app.core.redis_manager_v2.redis_client import RedisClient
            from app.configs import AppConfig
            from redis.asyncio import Redis

            config = AppConfig.create()
            redis_config = config.infrastructure.redis
            raw_redis_client = Redis(
                host=redis_config.host,
                port=redis_config.port,
                db=redis_config.db,
                password=redis_config.password,
                decode_responses=True,
            )
            redis_client_wrapper = RedisClient(redis_client=raw_redis_client)
            httpx_client_handler = HttpxClientHandler()
            logger.warning(
                "event=wb_manager_hub_fallback_created "
                "fallback_wb_manager_hub_created=true shop_id=%s reason=%s "
                "caller=%s handler_id=%s",
                complex_adv.shop_id,
                "missing_context",
                _get_caller_name(),
                id(httpx_client_handler),
            )

            wb_manager_hub_container = WBManagerHubContainer(
                _shop_id=complex_adv.shop_id,
                _httpx_client_handler=httpx_client_handler,
                _redis_wrapper=redis_client_wrapper,
            )
            logger.warning(
                "event=wb_manager_hub_container_created shop_id=%s "
                "handler_id=%s caller=%s fallback=%s",
                complex_adv.shop_id,
                id(httpx_client_handler),
                _get_caller_name(),
                True,
            )
            return wb_manager_hub_container.wb_manager_hub()

    @staticmethod
    async def _set_calculated_keywords_in_redis_cache(complex_adv: 'ComplexAdv',
                                                      calculated_keyword_list: list[CalculatedKeyword]) -> None:
        redis_cache_manager = RedisCalculatedKeywordsCacheManager()
        await redis_cache_manager.set_calculated_keywords(calculated_keyword_list, complex_adv.adv_id)

    @staticmethod
    async def _get_bidder_keyword_statuses(
        complex_adv: 'ComplexAdv',
        texts: list[str],
    ) -> dict[str, BidderKeywordStatus]:
        wb_manager_hub = await CalculatedKeywordsManager._get_wb_manager_hub(complex_adv)

        redis_manager_instance: RedisKeywordBidderStatusManager = (
            wb_manager_hub.redis_keyword_bidder_status_manager
        )
        if isinstance(redis_manager_instance, providers.Provider):
            redis_manager_instance = cast(
                RedisKeywordBidderStatusManager, redis_manager_instance() # noqa
            )

        statuses_map: dict[str, BidderKeywordStatus] = await redis_manager_instance.get_statuses(
            complex_adv, texts
        )
        return statuses_map


def _get_caller_name() -> str:
    """Вернуть ближайший внешний caller для diagnostic fallback-log."""
    stack = inspect.stack()
    if len(stack) < 3:
        return "—"
    return stack[2].function
