import asyncio
import logging
import typing

from sqlalchemy import select
from sqlalchemy.orm import load_only

from app.utils.db.session_maker import get_async_session_maker

from . import models, wb_db_manager
from .data_classes.adv import Adv
from .models.wb_cabinet import WBCabinet

if typing.TYPE_CHECKING:
    from ...shop_runner.modules.wb_api import WBApi

sm = get_async_session_maker

logger = logging.getLogger(__name__)

_coroutine_parallel_run_queue = asyncio.Queue()


async def consumer():
    logger.info("Consumer started")
    active_tasks = []
    while True:
        logger.info("Consumer waiting for task")
        if _coroutine_parallel_run_queue.empty() and active_tasks:
            logger.info("Consumer waiting for task")
            done, _ = await asyncio.wait(
                active_tasks, return_when=asyncio.FIRST_COMPLETED
            )
            # Удалять задачи из списка active_tasks здесь не нужно, так как мы используем колбэки для их удаления
        else:
            coroutine: asyncio.Future = await _coroutine_parallel_run_queue.get()
            task = asyncio.create_task(coroutine)
            task.add_done_callback(lambda t, lst=active_tasks: lst.remove(t))
            active_tasks.append(task)
        await asyncio.sleep(1)


class ShopDataUpdater:
    def __repr__(self):
        return f"{self.wb_cabinet.shop_id}"

    def __init__(self, wb_api: "WBApi"):
        self.wb_api = wb_api
        wb_cabinet = wb_api.wb_cabinet
        assert wb_cabinet, "Нет кабинета"
        self.wb_cabinet: WBCabinet = wb_cabinet
        pass

    async def quick_update_all_data(self):
        await self.__quick_update_advs()

    async def __quick_update_advs(self):
        wb_api = self.wb_api
        advert_api = wb_api
        adv_ids: list[int] = await advert_api.get_advertIds()
        async with sm() as session:
            stmt = select(models.AdvSetting).where(
                models.AdvSetting.adv_id.in_(adv_ids)
            )
            exist_advs_result = (await session.execute(stmt)).unique()
            existing_advs: list[models.AdvSetting] = exist_advs_result.scalars().all()
            existind_advs_ids: set[int] = {adv.adv_id for adv in existing_advs}
            not_existing_adv_ids: set[int] = set(adv_ids) - existind_advs_ids
            if not_existing_adv_ids:
                await self.__quick_update_advs_in_db(not_existing_adv_ids)
            func = self.__quick_update_advs_in_db(existind_advs_ids)
            await _coroutine_parallel_run_queue.put(func)

    async def __quick_update_advs_in_db(self, adv_ids: set[int]) -> None:
        wb_api = self.wb_api
        advs = await wb_api.get_advs(list(adv_ids))
        nmids_collection = set()
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        for adv in advs:
            nmids = adv.nmids
            if nmids:
                for nmid in nmids:
                    nmids_collection.add(nmid)
        cards = await wb_api.get_all_cards()
        await wb_db_manager.update_cards_in_db(cards, self.wb_cabinet)

    async def update_advs_data(self) -> list[Adv]:
        # adv_ids берём из БД по кампаниям с bot_active; обновляем и авто-, и поисковые РК
        wb_api: WBApi = self.wb_api
        advert_api = wb_api

        adv_ids: list[int] = []
        async with sm(read_only=True) as session:
            stmt = (
                select(models.AdvSetting)
                .where(
                    models.AdvSetting.wb_cabinet_id == self.wb_cabinet.id,
                    models.AdvSetting.bot_active.is_(True),
                )
                .options(
                    load_only(
                        models.AdvSetting.name,
                        models.AdvSetting.adv_id,
                        models.AdvSetting._search_adv_id,
                    )
                )
            )
            result = await session.execute(stmt)
            adv_settings = result.unique().scalars().all()
        for adv_setting in adv_settings:
            if adv_setting.adv_id is not None:
                adv_ids.append(adv_setting.adv_id)
            search_id = adv_setting.search_adv_id
            if search_id is not None:
                adv_ids.append(search_id)
        adv_ids = list(dict.fromkeys(adv_ids))  # порядок сохраняем, дубли убираем

        if not adv_ids:
            return []
        logger.debug(f"Получены adv_ids: {len(adv_ids)} штук")
        advs: list[Adv] = await advert_api.get_advs(adv_ids)
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        logger.debug("Обновление в базе advs завершено")
        return advs

    async def update_cards_data(self) -> None:
        wb_api = self.wb_api
        cards = await wb_api.get_all_cards()
        await wb_db_manager.update_cards_in_db(cards, self.wb_cabinet)
        logger.debug("Обновление карточек в базе завершено")
