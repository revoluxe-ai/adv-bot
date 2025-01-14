import asyncio
from datetime import datetime

from . import wb_data_getter
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
import typing
import logging

from ..wb_adv_updater import data_manager

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.api import FullAdvStat
from . import db_data_manager

from app.utils import redis_manager

logger = logging.getLogger(__name__)

class ShopUpdater:
    def __init__(self, access: WBCabinetAccess):
        from app.modules.common_slaves.wildberries.api import WBApi
        self.access = access
        self.shop_id = access.wb_cabinet.shop_id
        self.wb_api = WBApi(access)

    async def __call__(self):
        while True:
            try:
                adv_ids = await self._get_active_adv_ids()
                if adv_ids:
                    await self._update_for_last_days_in_redis_run(adv_ids)
            except:
                logger.error(f'Ошибка обновления данных для магазина shop_id={self.shop_id}', exc_info=True)
            finally:
                await asyncio.sleep(120)


    async def __update_full_advs_stats_in_redis(self, adv_ids: list[int]):
        full_stats: list['FullAdvStat'] = await wb_data_getter.get_full_adv_stat_for_adv_ids(self.wb_api,
                                                                                           adv_ids,
                                                                                           threshold_dates=30)
        if full_stats:
            await redis_manager.set_full_stat_adv(full_stats)
            date_time = datetime.now()
            for stat in full_stats:
                await data_manager.set_last_full_stat_update(stat.advertId, date_time)




    async def _update_for_last_days_in_redis_run(self, adv_ids: list[int]):
        while True:
            try:
                await self.__update_full_advs_stats_in_redis(adv_ids)
                logger.debug(f'Данные для магазина shop_id={self.shop_id} обновлены')
            except:
                logger.error(f'Ошибка обновления данных для магазина shop_id={self.shop_id}', exc_info=True)
            finally:
                await asyncio.sleep(120)


    async def _get_active_adv_ids(self)-> list[int]:
        adv_ids = await db_data_manager.get_active_adv_ids(self.shop_id)
        return adv_ids

    # async def _update_full_adv_stat_in_redis_for_all_shop_active_advs(self, adv_ids: list[int]):
    #     full_adv_stat_by_adv_id: dict = self.wb_api.advert.get_adv_full_state(adv_ids, pass_days=30)
    #     await asyncio.gather(*[self._update_adv_data(adv_id) for adv_id in adv_ids])
    #


async def _async_process_run():
    while True:
        try:
            await async_process_run()
        except:
            logger.error('Ошибка асинхронного процесса', exc_info=True)
            await asyncio.sleep(60)



async def async_process_run():
    tasks = {}
    while True:
        all_shop_ids = await db_data_manager.get_all_active_shop_ids_with_active_advs()
        # all_shop_ids = ['84f86c01-137d-5992-8f62-614d5f119bd1']
        for shop_id in all_shop_ids:
            if shop_id not in tasks:
                access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
                shop_updater = ShopUpdater(access)
                tasks[shop_id] = asyncio.create_task(shop_updater())
            else:
                if tasks[shop_id].done():
                    if tasks[shop_id].exception():
                        logger.error(f'Ошибка выполнения задачи: {tasks[shop_id].exception()}', exc_info=True)
                    del tasks[shop_id]

        await asyncio.sleep(1)





    # access_coroutines = [super_cabinet_manager.get_access_for_wb_cabinet(shop_id) for shop_id in all_shop_ids]
    # tasks = []
    # for access_future in asyncio.as_completed(access_coroutines):
    #     access = await access_future
    #     full_shop_update_func: typing.Callable = ShopUpdater(access)
    #     tasks.append(asyncio.create_task(full_shop_update_func()))  # Запуск задачи сразу
    #
    # for task in asyncio.as_completed(tasks):
    #     try:
    #         await task
    #     except Exception as e:
    #         logger.error(f'Ошибка выполнения задачи: {e}', exc_info=True)

