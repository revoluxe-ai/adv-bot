import asyncio
from app.modules.common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess

import logging

from ..wb_adv_cpm_manager.wb_api import WBApi

from . import db_data_manager

from ..common_slaves.wildberries.api import WBApi

logger = logging.getLogger(__name__)

class FullStatAdvUpdater:
    def __init__(self, access: WBCabinetAccess):

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





    async def _update_for_last_days_in_redis_run(self, adv_ids: list[int]):
        while True:
            try:
                await self.__update_full_advs_stats_in_redis(adv_ids)
                logger.debug(f'Данные для магазина shop_id={self.shop_id} обновлены')
            except Exception as exc:
                logger.error(f'Ошибка обновления данных для магазина shop_id={self.shop_id}, ошибка: {exc}')
            finally:
                await asyncio.sleep(120)


    async def _get_active_adv_ids(self)-> list[int]:
        adv_ids = await db_data_manager.get_active_adv_ids(self.shop_id)
        return adv_ids

    # async def _update_full_adv_stat_in_redis_for_all_shop_active_advs(self, adv_ids: list[int]):
    #     full_adv_stat_by_adv_id: dict = self.wb_api.advert.get_adv_full_state(adv_ids, pass_days=30)
    #     await asyncio.gather(*[self._update_adv_data(adv_id) for adv_id in adv_ids])
    #


async def new_update_shop_loop():
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
        for shop_id in all_shop_ids:
            if shop_id not in tasks:
                access = await super_cabinet_manager.get_access_for_wb_cabinet(shop_id)
                shop_updater = FullStatAdvUpdater(access)
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

