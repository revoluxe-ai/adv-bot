import asyncio
from sqlalchemy import select
from . import models
from app.utils.db.session_maker import get_async_session_maker
import logging
from . import wb_db_manager
import typing

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.common_slaves.wildberries.api import WBApi
from .data_classes.adv import Adv
from .models import WBCabinet
sm = get_async_session_maker

logger = logging.getLogger(__name__)

_coroutine_parallel_run_queue = asyncio.Queue()


async def consumer():
    logger.info('Consumer started')
    active_tasks = []
    while True:
        logger.info('Consumer waiting for task')
        if _coroutine_parallel_run_queue.empty() and active_tasks:
            logger.info('Consumer waiting for task')
            done, _ = await asyncio.wait(active_tasks, return_when=asyncio.FIRST_COMPLETED)
            # Удалять задачи из списка active_tasks здесь не нужно, так как мы используем колбэки для их удаления
        else:
            coroutine: asyncio.Future = await _coroutine_parallel_run_queue .get()
            task =  asyncio.create_task(coroutine)
            task.add_done_callback(lambda t, lst=active_tasks: lst.remove(t))
            active_tasks.append(task)
        await asyncio.sleep(1)

class ShopDataUpdater:

    def __repr__(self):
        return f'{self.wb_cabinet.shop_id}'

    def __init__(self, wb_access:  'WBCabinetAccess'):
        self.wb_api = WBApi(wb_access)
        self.wb_cabinet: WBCabinet = wb_access.wb_cabinet
        pass


    async def update_all_shop_data(self):
        await asyncio.gather(self.update_advs_data(),
                             self.update_advs_data())


    async def quick_update_all_data(self):
        await self.__quick_update_advs()


    async def __quick_update_advs(self):
        wb_api  = self.wb_api
        advert_api = wb_api.advert
        adv_ids: list[Adv] = await advert_api.get_advertIds()
        async with sm() as session:
            stmt = select(models.AdvSetting).where(models.AdvSetting.adv_id.in_(adv_ids))
            result = (await session.execute(stmt)).unique()
            existing_advs: list[models.AdvSetting] = result.scalars().all()
            existind_advs_ids: set[int] = {adv.adv_id for adv in existing_advs}
            not_existing_adv_ids: set[int] = set(adv_ids) - existind_advs_ids
            if not_existing_adv_ids:
                await self.__quick_update_advs_in_db(not_existing_adv_ids)
            func = self.__quick_update_advs_in_db(existind_advs_ids)
            await _coroutine_parallel_run_queue.put(func)


    async def __quick_update_advs_in_db(self, adv_ids:set[int]):
        wb_api = self.wb_api
        advs = await wb_api.advert.get_advs(list(adv_ids))
        nmids_collection = set()
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        for adv in advs:
            nmids = adv.nmids
            if nmids:
                for nmid in nmids:
                    nmids_collection.add(nmid)
        async def update_cards():
            cards = await wb_api.content.get_all_cards()
            await wb_db_manager.update_cards_in_db(cards, self.wb_cabinet)
        func = update_cards()
        await _coroutine_parallel_run_queue.put(func)


    async def update_advs_data(self) -> list[Adv]:
        logger.debug(f'Обновление данных для кабинета {self.wb_cabinet.shop_id}')
        wb_api: WBApi = self.wb_api
        advert_api = wb_api.advert
        adv_ids = await advert_api.get_advertIds()
        logger.debug(f'Получены adv_ids: {len(adv_ids)} штук')
        advs: list[Adv] = await advert_api.get_advs()
        await wb_db_manager.update_advs_in_db(advs, self.wb_cabinet.id)
        logger.debug(f'Обновление в базе advs завершено')
        return advs



    async def update_cards_data(self):
        wb_api = self.wb_api
        cards = await wb_api.content.get_all_cards()
        await wb_db_manager.update_cards_in_db(cards, self.wb_cabinet)
        logger.debug(f'Обновление карточек в базе завершено')
