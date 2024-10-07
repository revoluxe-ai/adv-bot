import asyncio
from app.utils.db.session_maker import get_async_session_maker as sm
from . import rel_db as pg
from .. import data_manager
from ...common_slaves.wildberries import super_cabinet_manager
from ...common_slaves.wildberries.api import WBApi
from ...common_slaves.wildberries.models import AdvSetting
import logging
from .types import FullAdvStat
logger = logging.getLogger(__name__)









class AdvDataUpdater:
    def __init__(self, adv_setting, access):
        self._adv_setting = adv_setting
        self._access = access
        self._adv_id = adv_setting.adv_id


    async def run_update_full_adv_statistic(self):
        try:
            await self._run_update_full_adv_statistic()
        except Exception as exc:
            logger.error(f'Ошибка при обновлении полной статистики для кампании с adv_id {self._adv_setting.adv_id}', exc_info=True)

    async def _run_update_full_adv_statistic(self):
        wb_api = WBApi(self._access)
        adv_id = self._adv_id
        full_statistics_for_last_30_days: list[FullAdvStat] = await wb_api.advert.get_full_adv_statistic(adv_id, 30)













async def _update_wb_adv_data(adv_setting):
    access = await super_cabinet_manager.get_access_for_wb_cabinet(adv_setting.wb_cabinet_id)
    adv_data_updater = AdvDataUpdater(adv_setting, access)
    await asyncio.gather(
        adv_data_updater.run_update_full_adv_statistic(),
        )


async def _run_update_for_bot_active_advs():
    tasks = {}
    while True:
        adv_settings: list[AdvSetting] = await pg.get_active_adv_settings()
        if not adv_settings:
            await asyncio.sleep(1)
            continue
        for adv_setting in adv_settings:
            adv_id = adv_setting.adv_id
            if adv_id in tasks:
                if tasks[adv_id].done():
                    if tasks[adv_id].exception():
                        logger.error(f'Ошибка при обновлении данных для кампании с adv_id {adv_id}',
                                     exc_info=True)
                    del tasks[adv_id]
            task = asyncio.create_task(_update_wb_adv_data(adv_setting))
            tasks[adv_setting.adv_id] = task
        await asyncio.sleep(1)


async def run_update_wb_data_to_redis():
    await asyncio.gather(
        _run_update_for_bot_active_advs(),




