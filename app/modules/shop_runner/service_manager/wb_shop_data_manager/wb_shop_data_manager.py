import asyncio
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import (
    NormqueryBidDTO,
)
from app.core.mp.wb.api.managers import WBDataManager
from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.services.update_cluster_bids_manager.wb_manager import (
    WBManager,
)
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.plan_fact import PlanFactProvider
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)
from app.modules.shop_runner.service_manager.services.plan_fact_controller.plan_fact_reader import (
    PlanFactReader,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
    PlanData,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import (
    ComplexAdv,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.pre_complex_adv import (
    PreComplexAdv,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.shop_runner.service_manager.wb_shop_data_manager.single_run_decorator import (
    single_run,
)
from app.modules.shop_runner.tasks_manager.tasks_manager import (
    TasksManager,
    run_tasks,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.settings import settings
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO
from app.utils.db.session_maker import get_async_session_maker as sm

logger = logging.getLogger(__name__)


@dataclass
class WBAdvDataParts:
    complex_adv: ComplexAdv
    plan: PlanData
    fact: FactData
    keywords: list[CalculatedKeyword]
    current_common_bids_in_search_adv: dict[int, int] | None


class WBShopDataManager:
    def __init__(
        self,
        wb_cabinet: WBCabinet,
        tasks_manager: TasksManager,
        wb_api_data_manager : WBDataManager,
        wb_manager: WBManager | None,
        plan_fact_reader: PlanFactReader,
    ):
        self._wb_cabinet: WBCabinet = wb_cabinet
        self.shop_id: str = wb_cabinet.shop_id
        self._tasks_manager: TasksManager | None = tasks_manager
        self._wb_api_data_manager = wb_api_data_manager
        self._wb_manager = wb_manager
        self._plan_fact_reader = plan_fact_reader
        self._traffic_clicks_manager = TrafficClicksManager()

    @single_run()
    async def __get_calculated_keywords(
        self,
        complex_adv: ComplexAdv,
        *,
        cache_only: bool = True,
    ) -> list[CalculatedKeyword]:
        """Только Redis ``calculated_keywords:{adv_id}`` (прогрев — snapshot updater).

        Args:
            complex_adv: комплекс, для которого читаются keywords.
            cache_only: keyword-only параметр ``GetKeywordsProvider``;
                отклонение ``False`` — в ``ComplexAdv.get_keywords``.

        Raises:
            ShopRunnerKeywordsCacheMissError: hash отсутствует.
        """
        _ = cache_only  # Protocol GetKeywordsProvider; guard — ComplexAdv.get_keywords
        from app.modules.shop_runner.required_data_miss import (
            fetch_calculated_keywords_from_redis,
        )
        if settings.CAN_NOT_CACHE_DATA:
            from app.modules.wb_adv_updater.calculated_keywords_manager import CalculatedKeywordsManager
            calc_kw_manager = CalculatedKeywordsManager()
            return await calc_kw_manager.get_calculated_keywords(complex_adv)
        return await fetch_calculated_keywords_from_redis(
            complex_adv.adv_id,
            shop_id=complex_adv.shop_id or self.shop_id,
        )

    @single_run()
    async def _get_advs(self, only_bot_active: bool) -> list[AdvSetting]:
        shop_id = self.shop_id
        async with sm(read_only=True) as session:
            return await self.__get_advs(session, shop_id, only_bot_active)

    @staticmethod
    async def __get_advs(session: AsyncSession,
                         shop_id: str,
                         only_bot_active: bool) -> list[AdvSetting]:
        stmt = (
            select(AdvSetting)
            .join(AdvSetting.wb_cabinet)
            .where(WBCabinet.shop_id == shop_id,
                   AdvSetting.active_status != 'done', )
        )

        if only_bot_active:
            stmt = stmt.where(AdvSetting.bot_active.is_(True))

        result = await session.execute(stmt)
        advs: Sequence[AdvSetting] = result.scalars().all()
        adv_settings_list = list(advs)
        if not adv_settings_list:
            raise NotFoundActiveAdvCompany("Нет активных кампаний")
        return adv_settings_list


    async def _get_adv_id_to_search_adv_map(
        self,
        search_id_ids: set[int],
    ) -> dict[int, AdvSetting]:
        """PURE_READ parent: открывает ``sm(read_only=True)`` и делегирует child."""
        async with sm(read_only=True) as session:
            return await self.__get_adv_id_to_search_adv_map(session, search_id_ids)

    @staticmethod
    async def __get_adv_id_to_search_adv_map(
        session: AsyncSession,
        search_id_ids: set[int],
    ) -> dict[int, AdvSetting]:
        """Загрузить AdvSetting по ``adv_id`` через переданную read-only session.

        Parent ``_get_adv_id_to_search_adv_map`` открывает ``sm(read_only=True)``.

        Args:
            session: SQLAlchemy AsyncSession (PURE_READ).
            search_id_ids: множество ``adv_id`` поисковых РК.

        Returns:
            Словарь ``adv_id → AdvSetting``.
        """
        stmt = select(AdvSetting).where(AdvSetting.adv_id.in_(search_id_ids))
        result = await session.execute(stmt)
        advs: Sequence[AdvSetting] = result.scalars().all()
        adv_dict: dict[int, AdvSetting] = {adv.adv_id: adv for adv in advs}
        return adv_dict

    @single_run()
    async def get_wb_advs_dto(
        self,
        complex_advs: list[ComplexAdv],
        search_adv_bids_override: dict[int, dict[int, int]] | None = None,
    ) -> list[WBAdvDTO]:
        complex_advs = [adv for adv in complex_advs if adv.bot_active]
        complex_advs_with_search_adv: list[ComplexAdv] = []
        for complex_adv in complex_advs:
            search_adv_id = complex_adv.search_adv_id
            if search_adv_id is None:
                logger.error('Нет Поисковой Кампании в Коплексе, пропускаю')
                continue
            complex_advs_with_search_adv.append(complex_adv)

        complex_advs = complex_advs_with_search_adv

        if not complex_advs:
            return []
        reuse_min_bids = self._reuse_shared_min_bids_from_complex_advs(complex_advs)

        if search_adv_bids_override is not None:
            if reuse_min_bids is not None:
                min_bids = reuse_min_bids
            else:
                min_bids = await self._get_min_bids(complex_advs, cache_possible=True)
            search_adv_bids = search_adv_bids_override
        else:
            if reuse_min_bids is not None:
                min_bids = reuse_min_bids
                search_adv_bids = await self._get_search_adv_common_bids(
                    complex_advs
                )
            else:
                # TODO: Вынести получение данных по API отсюда
                gathered = await asyncio.gather(
                    self._get_min_bids(complex_advs, cache_possible=True),
                    self._get_search_adv_common_bids(complex_advs),
                )
                min_bids = gathered[0]
                search_adv_bids = gathered[1]

        if min_bids is None:
            raise RuntimeError("Missing min_bids for advs")

        handlers: list[Callable[[], Awaitable[WBAdvDataParts]]] = []

        complex_advs_with_bids: list[ComplexAdv] = []
        for complex_adv in complex_advs:
            search_adv_id = complex_adv.search_adv_id
            current_search_bids = (
                search_adv_bids.get(search_adv_id)
                if search_adv_id is not None
                else None
            )
            complex_advs_with_bids.append(complex_adv)
            search_bids_snapshot = current_search_bids

            async def _collect_handler(
                _adv: ComplexAdv = complex_adv,
                _bids: dict[int, int] | None = search_bids_snapshot,
            ) -> WBAdvDataParts:
                return await self._collect_adv_data_parts(_adv, _bids)

            handlers.append(_collect_handler)

        max_workers = max(1, min(len(handlers), 16))
        # Важно: здесь может быть вложенный вызов из handler-а shared TasksManager
        # (adv_settings_auto_update -> process_adv_v3 -> get_wb_advs_dto).
        # Если передать тот же tasks_manager при max_workers=1, получится self-queue deadlock.
        results = await run_tasks(
            handlers,
            max_workers=max_workers,
            tasks_manager=None,
            return_exceptions=True,
        )

        successful_parts: list[WBAdvDataParts] = []
        for adv, result in zip(complex_advs_with_bids, results):
            if isinstance(result, BaseException):
                logger.error(
                    "Ошибка сбора план-факта для adv_id=%s shop_id=%s: %s",
                    adv.adv_id,
                    adv.shop_id,
                    result,
                )
                continue
            successful_parts.append(result)

        return [
            self._build_wb_adv_dto_from_parts(parts, min_bids)
            for parts in successful_parts
        ]


    @staticmethod
    def _reuse_shared_min_bids_from_complex_advs(
        complex_advs: list[ComplexAdv],
    ) -> AdvMinNmidsBids | None:
        if not complex_advs:
            return None
        first_bids = complex_advs[0].min_nmids_bids
        if first_bids is None:
            return None
        if not all(a.min_nmids_bids is first_bids for a in complex_advs):
            return None
        return first_bids

    @staticmethod
    async def _collect_plan_data(complex_adv: ComplexAdv) -> PlanData:
        plan = PlanFactProvider.get_plan_data(complex_adv.adv_setting)
        if plan is None:
            raise RuntimeError(
                "Plan data is not configured for adv_id=%s" % complex_adv.adv_id
            )
        return plan


    @staticmethod
    async def _collect_keywords(complex_adv: ComplexAdv) -> list[CalculatedKeyword]:
        """Keywords для WBAdvDTO только из Redis (``calculated_keywords:{adv_id}``).

        Raises:
            ShopRunnerKeywordsCacheMissError: hash в Redis отсутствует — нужен snapshot updater.
        """
        from app.snapshot_data_updater.adapters.wb_adv_dto_adapter import (
            WBAdvDtoSnapshotAdapter,
        )

        adapter = WBAdvDtoSnapshotAdapter()
        shop_id = complex_adv.shop_id or ""
        cached = await complex_adv.get_keywords()
        await adapter.shadow_log_keywords_delta(
            shop_id, complex_adv.adv_id, legacy_count=len(cached)
        )
        return cached


    async def _collect_adv_data_parts(
        self,
        complex_adv: ComplexAdv,
        current_search_bids: dict[int, int] | None,
    ) -> WBAdvDataParts:
        plan = await self._collect_plan_data(complex_adv)
        keywords = await self._collect_keywords(complex_adv)
        manager = PlanFactProvider(complex_adv.adv_setting)
        stat = await manager.get_stat_data(keywords)
        fact = await manager.get_fact_data(stat)

        return WBAdvDataParts(
            complex_adv=complex_adv,
            plan=plan,
            fact=fact,
            keywords=keywords,
            current_common_bids_in_search_adv=current_search_bids,
        )

    @single_run()
    async def get_pre_complex_advs(
        self,
        *,
        skip_plan_fact: bool = False,
        only_bot_active: bool,
    ) -> list[PreComplexAdv]:
        """Собрать PreComplexAdv из PG.

        Args:
            skip_plan_fact: не ходить в ClickHouse за plan_fact_stats. Используется
                для корутин, где факт подгружается отдельно, например
                ``update_cluster_bids``.
            only_bot_active: Вернуть только AdvSetting.bot_active=True.

        Важно:
            Это точка, где должен быть синхронизирован auto common budget.
            Если здесь не пересчитать ``common_budget_daily_limit`` по актуальным
            plan-fact данным при включённом ``auto_common_budget``, downstream
            продолжит работать с устаревшим in-memory лимитом и общий бюджет
            не применится.
        """
        adv_settings: list[AdvSetting] = await self._get_advs(only_bot_active)

        self._set_auto_commom_budget(adv_settings)
        search_adv_ids: set[int] = {
            adv.search_adv_id for adv in adv_settings if adv.search_adv_id
        }

        adv_ids_for_plan_fact = [adv.adv_id for adv in adv_settings]
        summaries_by_adv_id = {}
        if skip_plan_fact:
            plan_fact_reader = None
        else:
            plan_fact_reader = self._plan_fact_reader

        if search_adv_ids:
            search_adv_task = self._get_adv_id_to_search_adv_map(search_adv_ids)
            if plan_fact_reader is not None:
                search_adv_idv, summaries_by_adv_id = await asyncio.gather(
                    search_adv_task,
                    plan_fact_reader.get_latest_plan_facts(adv_ids_for_plan_fact),
                )
            else:
                search_adv_idv = await search_adv_task
        else:
            search_adv_idv = {}
            if plan_fact_reader is not None:
                summaries_by_adv_id = await plan_fact_reader.get_latest_plan_facts(
                    adv_ids_for_plan_fact
                )

        return [
            PreComplexAdv(
                auto_adv=adv,
                plan_data=PlanFactProvider.get_plan_data(adv),
                plan_fact_summary=summaries_by_adv_id.get(adv.adv_id),
                search_adv=(
                    search_adv_idv.get(adv.search_adv_id)
                    if adv.search_adv_id is not None
                    else None
                ),
            )
            for adv in adv_settings
        ]

    @single_run()
    async def get_complex_advs(
        self,
        *,
        only_bot_active:bool = True,
        load_extras: bool = True,
        skip_plan_fact: bool = False,
    ) -> list["ComplexAdv"]:
        """Собрать активные комплексы РК.

        ``load_extras=True`` (по умолчанию): обогатить traffic-кликами (CH) и подтянуть
        min bids — дорого при большом числе РК. Нужно для ``change_adv_strategy``
        (сравнение ``organic_clicks`` / ``shelf_clicks`` в ``AdvStrategySelector``).

        ``load_extras=False``: только данные из БД + nmids; для ``adv_settings_auto_update``
        и прочих фоновых корутин — без ``traffic_clicks_dto`` (полочный gate по кликам не сработает).

        ``skip_plan_fact=True``: не читать ``plan_fact_stats`` в CH при сборке pre_complex
        (факт для ``update_cluster_bids`` приходит из ``PlanFactReader`` в менеджере ставок).
        """
        # TODO(single_run/reentrancy): Важно: `get_complex_advs()` и `get_pre_complex_advs()`
        # оба помечены `@single_run()`.
        #
        # Наш `single_run` реализован не через re-entrant lock, а через per-key "single-flight"
        # на `asyncio.Event` (см. `single_run_decorator.py`). Это означает:
        # - параллельные вызовы ОДНОГО и того же метода с одинаковыми args/kwargs будут ждать
        #   один общий event и получать общий результат;
        # - при этом повторный вход В ТОТ ЖЕ метод с теми же args/kwargs до завершения первого
        #   вызова приводит к self-deadlock (второй вход будет ждать event, который выставит
        #   только первый вход, но первый вход уже ждёт второго по цепочке вызовов).
        #
        # Текущее вложение `get_complex_advs()` -> `get_pre_complex_advs()` само по себе НЕ
        # обязано дедлочиться, т.к. ключ в `single_run` включает имя функции, и это разные key.
        # Однако это место становится "точкой риска" для будущих рефакторингов:
        # достаточно случайно получить цикл вида
        # `get_complex_advs()` -> ... -> `get_pre_complex_advs()` -> ... -> `get_complex_advs()`
        # (или запуск фоновой задачи, которая внутри снова вызовет `get_complex_advs()`), и мы
        # получим вечное ожидание.
        #
        # Что нужно сделать позже (выбрать один вариант):
        # - добавить в `single_run` явную защиту от re-entrance в рамках одной asyncio.Task
        #   (например, task-local стек ключей через `contextvars`): либо разрешать re-entrance
        #   (re-entrant single-flight), либо падать с понятной ошибкой вместо "вечного await";
        # - или убрать `@single_run()` с одного из методов и оставить single-flight на одном
        #   уровне (например, только на `get_complex_advs()`), чтобы исключить циклы;
        # - или сделать общий "seed" метод без декоратора и вызывать его из обоих путей.
        pre_complex_advs: list[PreComplexAdv] = await self.get_pre_complex_advs(
            only_bot_active=only_bot_active,
            skip_plan_fact=skip_plan_fact)
        complex_advs: list[ComplexAdv] = []
        for pre_adv in pre_complex_advs:
            complex_adv = ComplexAdv(
                shop_id=self.shop_id,
                adv_setting=pre_adv.auto_adv,
                get_keywords_func=self.__get_calculated_keywords,
                search_adv=pre_adv.search_adv,
                target_pay_for_order=pre_adv.resolved_target_pay_for_order,
                fact_pay_for_order=pre_adv.plan_fact_summary.fact_pay_for_order if pre_adv.plan_fact_summary else None,
                resolve_cpo=pre_adv.resolved_target_pay_for_order,
            )
            complex_advs.append(complex_adv)
        handlers: list[Callable[[], Awaitable[None]]] = [
            lambda adv_=adv: self._traffic_clicks_manager.enrich(adv_)
            for adv in complex_advs
        ]
        if load_extras and handlers:
            results = await run_tasks(
                handlers,
                max_workers=max(1, min(len(handlers), 16)),
                tasks_manager=self._tasks_manager,
                return_exceptions=True,
            )
            for adv, result in zip(complex_advs, results):
                if isinstance(result, BaseException):
                    logger.error(
                        "Ошибка enrich traffic_clicks_dto, adv_id=%s shop_id=%s",
                        adv.adv_id,
                        adv.shop_id,
                        exc_info=result,
                    )
        # TODO: Нашел лютый баг: все падало, если хотя бы в 1 РК нет nmids
        complex_advs = [adv for adv in complex_advs if adv.nmids]
        complex_advs.sort(key=lambda adv: adv.adv_setting_original_id)
        if load_extras and complex_advs:
            await self.attach_min_nmids_bids(complex_advs)
        return complex_advs

    async def backfill_min_bids_for_adv(
        self,
        complex_adv: ComplexAdv,
    ) -> bool:
        """Догрузить min_bids в Redis для РК (как ``preload_min_bids_cache_miss``).

        Сначала ``refresh_min_bids_cache_miss_cells`` по cache-miss ячейкам;
        если ``main_nmid`` всё ещё нет — запрос к WB API и запись v2-кэша
        (``refresh_min_bids_cache``).

        Returns:
            True, если после догрузки ``main_nmid`` есть в ``min_bids.search``.
        """
        if self._wb_manager is None:
            logger.error(
                "backfill_min_bids_for_adv: WBManager недоступен shop_id=%s adv_id=%s",
                self.shop_id,
                complex_adv.adv_id,
            )
            return False

        nmid = complex_adv.main_nmid
        wb_manager = self._wb_manager

        async def _main_nmid_cached() -> bool:
            cached = await wb_manager.get_min_bids_cache_only(
                [complex_adv],
                context="v3_min_bids_check",
                apply_defaults=False,
            )
            return nmid in cached.search

        if await _main_nmid_cached():
            return True

        miss_cells = await wb_manager.find_min_bids_cache_miss_cells(
            [complex_adv],
            emit_app_log=True,
            log_label="v3_min_bids_backfill",
        )
        if miss_cells:
            try:
                written = await wb_manager.refresh_min_bids_cache_miss_cells(
                    miss_cells
                )
                logger.info(
                    "v3_min_bids_backfill: refresh miss shop_id=%s adv_id=%s "
                    "cells=%s written=%s",
                    self.shop_id,
                    complex_adv.adv_id,
                    len(miss_cells),
                    written,
                )
            except Exception:
                logger.error(
                    "v3_min_bids_backfill: refresh_min_bids_cache_miss_cells failed "
                    "shop_id=%s adv_id=%s",
                    self.shop_id,
                    complex_adv.adv_id,
                    exc_info=True,
                )

        if await _main_nmid_cached():
            return True

        logger.warning(
            "v3_min_bids_backfill: cache miss for main_nmid, WB API fallback "
            "shop_id=%s adv_id=%s nmid=%s",
            self.shop_id,
            complex_adv.adv_id,
            nmid,
        )
        try:
            await wb_manager.refresh_min_bids_cache([complex_adv])
        except Exception:
            logger.error(
                "v3_min_bids_backfill: refresh_min_bids_cache failed shop_id=%s adv_id=%s",
                self.shop_id,
                complex_adv.adv_id,
                exc_info=True,
            )
            return False

        if await _main_nmid_cached():
            return True

        logger.error(
            "v3_min_bids_backfill: main_nmid still missing after WB refresh "
            "shop_id=%s adv_id=%s nmid=%s",
            self.shop_id,
            complex_adv.adv_id,
            nmid,
        )
        return False

    async def attach_min_nmids_bids(self, complex_advs: list["ComplexAdv"]) -> None:
        """Подтянуть min_nmids_bids для переданных кампаний (без traffic enrich).

        Используется лёгкими корутинами (auto_shelf_bid_control), где load_extras=False.
        """
        if not complex_advs:
            return None
        try:
            min_bids = await self._get_min_bids(complex_advs, cache_possible=True)
        except Exception:
            logger.exception(
                "Ошибка получения min_bids (cache) в attach_min_nmids_bids, shop_id=%s",
                self.shop_id,
            )
            return None
        if min_bids is not None:
            for adv in complex_advs:
                adv.attach_min_nmids_bids(min_bids)
        return None

    @staticmethod
    def _build_wb_adv_dto_from_parts(
        parts: WBAdvDataParts, min_bids: AdvMinNmidsBids
    ) -> WBAdvDTO:
        return WBAdvDTO(
            complex_adv=parts.complex_adv,
            plan=parts.plan,
            fact=parts.fact,
            keywords=parts.keywords,
            current_common_bids_in_search_adv=parts.current_common_bids_in_search_adv,
            min_bids=min_bids,
        )

    async def _get_search_adv_common_bids(
        self, complex_advs: list[ComplexAdv]
    ) -> dict[int, dict[int, int]]:
        bids = await self._wb_api_data_manager.get_current_bids_for_advs(
            complex_advs
        )
        return self._aggregate_bids(bids)


    def aggregate_bids(self, bids: list[NormqueryBidDTO] | None,) -> dict[int, dict[int, int]]:
        return self._aggregate_bids(bids)


    @staticmethod
    def _aggregate_bids(
        bids: list[NormqueryBidDTO] | None,
    ) -> dict[int, dict[int, int]]:
        aggregated: dict[int, dict[int, int]] = {}
        if not bids:
            return aggregated
        for bid in bids:
            adv_bids = aggregated.setdefault(bid.advert_id, {})
            current_bid = adv_bids.get(bid.nm_id)
            adv_bids[bid.nm_id] = bid.bid if current_bid is None else max(
                current_bid, bid.bid
            )
        return aggregated

    async def _get_min_bids(
        self, complex_advs: list[ComplexAdv], cache_possible: bool
    ) -> AdvMinNmidsBids | None:
        if self._wb_manager is not None:
            if cache_possible:
                return await self._wb_manager.get_min_bids_cache_only(
                    complex_advs, context="wb_shop_data_manager"
                )
            return await self._wb_manager.get_min_bids(complex_advs, cache_possible=False)
        return await self._wb_api_data_manager.get_min_bids(complex_advs)

    @staticmethod
    def _set_auto_commom_budget(adv_settings: list[AdvSetting]) -> None:
        """Пересчитать ``common_budget_daily_limit`` в памяти для auto common budget.

        Вызывается из ``get_pre_complex_advs`` на каждом тике shop-runner. Меняет только
        in-memory ``AdvSetting``; в PostgreSQL лимит не сохраняется.

        При ``auto_common_budget=True`` и наличии ``max_price_for_order`` и
        ``plan_for_sales_for_day`` лимит = произведение. При выключенном авторасчёте или
        неполной конфигурации существующее значение не перезаписывается.
        """
        for adv in adv_settings:
            if not adv.auto_common_budget:
                continue
            max_pay = adv.max_price_for_order
            plan_sales = adv.plan_for_sales_for_day
            if max_pay is None or plan_sales is None:
                continue
            adv.common_budget_daily_limit = int(max_pay) * int(plan_sales)


# TODO: Реализовать гибкую модель управления через плавающую мощность и расчет потенциала от текущего статуса
