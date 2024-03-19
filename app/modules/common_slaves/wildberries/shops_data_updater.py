from .api import WBApi
import asyncio
from sqlalchemy import select
from . import models
from app.utils.db.session_maker import get_async_session_maker
import logging
from . import wb_db_manager


from app.modules.common_slaves.wildberries.models import WBUserCabinet
import app

sm = get_async_session_maker()

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
    def __init__(self, wb_api: WBApi, wb_user_cabinet: WBUserCabinet):
        self.__wb_api = wb_api
        self._wb_user_cabinet = wb_user_cabinet.wb_cabinet



    async def quick_update_all_data(self):
        await self.__update_advs()


    async def __update_advs(self):
        wb_api  = self.__wb_api
        advert_api = wb_api.advert
        adv_ids = await advert_api.get_advertIds(advert_api.live_company_status, advert_api.auto_adv_types)
        async with sm() as session:
            stmt = select(models.AdvSetting).where(models.AdvSetting.adv_id.in_(adv_ids))
            result = (await session.execute(stmt)).unique()
            existing_advs: list[models.AdvSetting] = result.scalars().all()
            existind_advs_ids = {adv.adv_id for adv in existing_advs}
            not_existing_adv_ids = set(adv_ids) - set(existind_advs_ids)
            if not_existing_adv_ids:
                await self.__update_advs_in_db(not_existing_adv_ids)
            func = self.__update_advs_in_db(existind_advs_ids)
            await _coroutine_parallel_run_queue.put(func)


    async def __update_advs_in_db(self, adv_ids:set[int]):
        wb_api = self.__wb_api
        advs = await wb_api.advert.get_advs(list(adv_ids))
        nmids_collection = set()
        await wb_db_manager.update_advs_in_db(advs, self._wb_user_cabinet)
        for adv in advs:
            nmids = adv.nmids
            if nmids:
                for nmid in nmids:
                    nmids_collection.add(nmid)

        func = wb_db_manager.update_cards_in_db(nmids_collection, self._wb_user_cabinet)
        await _coroutine_parallel_run_queue.put(func)

    # async def __update_cards(self, nmids:set[int]):
    #     cards = await self.__wb_api.advert.get_cards_by_text(nmids)
    #     await app.utils.db.db_manager.update_cards_in_db(cards, self._wb_user_cabinet)
    #


    async def update_all_data(self):
        wb_api = self.__wb_api
        advert_api = wb_api.advert
        adv_ids = await advert_api.get_advertIds(advert_api.live_company_status,
                                                 advert_api.auto_adv_types)
        advs = await advert_api.get_advs(adv_ids)

        await wb_db_manager.update_advs_in_db(advs, self._wb_user_cabinet)

        nmids = set()
        for adv in advs:
            nmids.update(adv.nmids)
        cards = await wb_api.advert.get_cards_by_text(nmids)
        await wb_db_manager.update_cards_in_db(cards, self._wb_user_cabinet)








