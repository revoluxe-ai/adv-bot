"""Обновление кампаний/карточек из WB и синхронизация локальных кэшей."""

import asyncio
import logging
import typing
from collections.abc import Coroutine, Mapping, Sequence
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.utils.db.session_maker import get_async_session_maker

from . import models, wb_db_manager
from .data_classes.adv import Adv
from .data_classes.card_from_wb import CardFromWB
from .models.wb_cabinet import WBCabinet

if typing.TYPE_CHECKING:
    from ...shop_runner.modules.wb_api import WBApi

sm = get_async_session_maker

logger = logging.getLogger(__name__)

# Типы Auto/Search РК v2 (unified=8, manual=9), для которых WB отдаёт recommendations bid.
_AUTO_RECOMMENDATIONS_BID_ADV_TYPES = frozenset({8, 9})

_QueueCoroutine = Coroutine[typing.Any, typing.Any, None]
_coroutine_parallel_run_queue: asyncio.Queue[_QueueCoroutine] = asyncio.Queue()


async def load_existing_advs_in_session(
    session: AsyncSession,
    adv_ids: Sequence[int],
) -> Sequence[models.AdvSetting]:
    """Вернуть существующие AdvSetting по adv_id из уже открытой PG-сессии."""
    if not adv_ids:
        return []
    stmt = select(models.AdvSetting).where(models.AdvSetting.adv_id.in_(adv_ids))
    exist_advs_result = (await session.execute(stmt)).unique()
    return exist_advs_result.scalars().all()


async def consumer() -> None:
    """Фоновый consumer очереди coroutine для параллельного обновления РК."""
    logger.info("Consumer started")
    active_tasks: list[asyncio.Task[None]] = []
    while True:
        logger.info("Consumer waiting for task")
        if _coroutine_parallel_run_queue.empty() and active_tasks:
            logger.info("Consumer waiting for task")
            _, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
            # Удалять задачи из списка active_tasks здесь не нужно, так как мы используем колбэки для их удаления
        else:
            coroutine = await _coroutine_parallel_run_queue.get()
            task = asyncio.create_task(coroutine)
            task.add_done_callback(lambda t, lst=active_tasks: lst.remove(t))
            active_tasks.append(task)
        await asyncio.sleep(1)


class ShopDataUpdater:
    """Синхронизирует кампании и карточки магазина из WB API в локальную БД/кэш."""

    def __repr__(self) -> str:
        return f"{self.wb_cabinet.shop_id}"

    class AutoRecommendationsBidCacheManager(Protocol):
        """Контракт cache manager для сохранения ставки полок Auto-кампаний."""

        async def set_bids(
            self,
            auto_adv_id: int,
            bids: dict[int, int],
        ) -> None: ...

    def __init__(
        self,
        wb_api: "WBApi",
        auto_recommendations_bid_cache_manager: AutoRecommendationsBidCacheManager
        | None = None,
    ) -> None:
        self.wb_api = wb_api
        wb_cabinet = wb_api.wb_cabinet
        assert wb_cabinet, "Нет кабинета"
        self.wb_cabinet: WBCabinet = wb_cabinet
        self._auto_recommendations_bid_cache_manager = (
            auto_recommendations_bid_cache_manager
        )

    async def quick_update_all_data(self) -> None:
        """Быстрое обновление кампаний кабинета (новые + существующие в очереди)."""
        await self.__quick_update_advs()

    async def __quick_update_advs(self) -> None:
        """Сверить adv_ids из WB с БД и поставить обновление существующих в очередь."""
        wb_api = self.wb_api
        advert_api = wb_api
        adv_ids: list[int] = await advert_api.get_advertIds()
        async with sm(read_only=True) as session:
            existing_advs = await load_existing_advs_in_session(session, adv_ids)
        existind_advs_ids: set[int] = {adv.adv_id for adv in existing_advs}
        not_existing_adv_ids: set[int] = set(adv_ids) - existind_advs_ids
        if not_existing_adv_ids:
            await self.__quick_update_advs_in_db(not_existing_adv_ids)
        func = self.__quick_update_advs_in_db(existind_advs_ids)
        await _coroutine_parallel_run_queue.put(func) # pyright: ignore

    async def __quick_update_advs_in_db(self, adv_ids: set[int]) -> None:
        """Обновить указанные РК и карточки в БД."""
        wb_api = self.wb_api
        advs = await wb_api.get_advs(list(adv_ids))
        nmids_collection: set[int] = set()
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        for adv in advs:
            nmids = adv.nmids
            if nmids:
                for nmid in nmids:
                    nmids_collection.add(nmid) # pyright: ignore
        cards = await wb_api.get_all_cards()

        # core CardFromWB и common_slaves CardFromWB — разные классы; cast на границе DB helper.
        await wb_db_manager.update_cards_in_db(
            typing.cast(list[CardFromWB], cards), self.wb_cabinet
        )
    async def update_advs_data(self) -> list[AuctionAdv]:
        """Загрузить РК кабинета из WB, сохранить в БД и обновить recommendations-bid кэш."""
        # adv_ids берём из БД по кампаниям с bot_active; обновляем и авто-, и поисковые РК
        wb_api: "WBApi" = self.wb_api
        advert_api = wb_api

        adv_ids: list[int] = []
        async with sm(read_only=True) as session:
           adv_settings = await self.get_adv_setting_by_wb_cabinet(session,
                                                                                      wb_cabinet_id=self.wb_cabinet.id,
                                                                                      )

        for adv_setting in adv_settings:
            adv_ids.append(adv_setting.adv_id)
            search_id = adv_setting.search_adv_id
            if search_id is not None:
                adv_ids.append(search_id)
        adv_ids = list(dict.fromkeys(adv_ids))  # порядок сохраняем, дубли убираем

        if not adv_ids:
            return []
        logger.debug(f"Получены adv_ids: {len(adv_ids)} штук")
        advs: list[AuctionAdv] = await advert_api.get_advs(adv_ids)
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        await self._cache_auto_recommendations_bids(advs)
        logger.debug("Обновление в базе advs завершено")
        return advs

    @staticmethod
    def _extract_auto_recommendations_bids(adv: Adv) -> dict[int, int]:
        """Извлечь recommendations bid по nmid из v2 payload, вложенного в legacy data.

        WB v2 кладёт ``recommendationsBidsByNmidKopecks`` и для type=8 (unified), и для
        type=9 (manual). Раньше учитывался только type=8 — manual Auto-РК не попадали
        в Redis-кэш, и auto_shelf increment останавливался на ``no_bid``.
        """
        if int(adv.type) not in _AUTO_RECOMMENDATIONS_BID_ADV_TYPES:
            return {}
        payload = adv.data
        raw_map = payload.get("recommendationsBidsByNmidKopecks")
        if not isinstance(raw_map, dict):
            return {}
        typed_map = typing.cast(Mapping[object, object], raw_map)
        result: dict[int, int] = {}
        for nmid_raw, bid_raw in typed_map.items():
            if not isinstance(nmid_raw, int):
                continue
            if not isinstance(bid_raw, int):
                continue
            if bid_raw <= 0:
                continue
            result[nmid_raw] = bid_raw
        return result

    async def _cache_auto_recommendations_bids(
        self, advs: Sequence[Adv]
    ) -> None:
        """Записать в Redis актуальные recommendations bid для auto кампаний."""
        manager = self._auto_recommendations_bid_cache_manager
        if manager is None:
            return None
        written_pairs = 0
        written_advs = 0
        skipped_advs = 0
        for adv in advs:
            bids = self._extract_auto_recommendations_bids(adv)
            if not bids:
                if int(adv.type) in _AUTO_RECOMMENDATIONS_BID_ADV_TYPES:
                    skipped_advs += 1
                continue
            await manager.set_bids(int(adv.advertId), bids)
            written_advs += 1
            written_pairs += len(bids)
        logger.info(
            "auto_recommendations_bid_cache_written shop_id=%s written_advs=%s written_pairs=%s skipped_auto_advs=%s",
            self.wb_cabinet.shop_id,
            written_advs,
            written_pairs,
            skipped_advs,
        )
        return None

    async def update_cards_data(self) -> None:
        """Загрузить все карточки магазина из WB и сохранить в БД."""
        wb_api = self.wb_api
        cards = await wb_api.get_all_cards()
        await wb_db_manager.update_cards_in_db(
            typing.cast(list[CardFromWB], cards), self.wb_cabinet
        )
        logger.debug("Обновление карточек в базе завершено")

    @staticmethod
    async def get_adv_setting_by_wb_cabinet(
        session: AsyncSession,
        *,
        wb_cabinet_id: int,
    ) -> Sequence[models.AdvSetting]:
        """Вернуть AdvSetting кабинета, у которых задан search_adv_id (колонка БД)."""
        stmt = (
            select(models.AdvSetting)
            .options(
                load_only(
                    models.AdvSetting.name,
                    models.AdvSetting.adv_id,
                    models.AdvSetting._search_adv_id,  # pyright: ignore[reportPrivateUsage]
                )
            ).where(
                models.AdvSetting.wb_cabinet_id == wb_cabinet_id,
            )
            .where(
                models.AdvSetting.wb_cabinet_id == wb_cabinet_id,))
        result = await session.execute(stmt)
        adv_settings = result.unique().scalars().all()
        return adv_settings
