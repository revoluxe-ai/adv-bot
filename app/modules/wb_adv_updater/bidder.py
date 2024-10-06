import logging

import aiohttp
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.api import WBApi
from app.modules.wb_adv_updater import data_manager
from ..common_slaves.wildberries import super_cabinet_manager
from app.modules.common_slaves.wildberries.models import WBCabinet
import asyncio
from sqlalchemy.future import select
from app.modules.common_slaves.wildberries.models import (
                                                          AdvSetting,
                                                          KeywordSetting)

from app.utils.db.session_maker import get_async_session_maker as sm
from ..common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from ...settings import settings
from ...utils import redis_manager
from  app.modules.wb_keywords_parser import parser
from ...utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)



async def run_bidder_process():
    while True:
        try:
            await _run_bidder_process()
        except Exception as e:
            logger.error(f'Ошибка процесса управления ставками {e}', exc_info=True)
        await asyncio.sleep(0)



async def _run_bidder_process():
    adv_tasks = {}
    while True:
       async with sm() as session:
           stmt = select(AdvSetting)\
               .join(AdvSetting.wb_cabinet)\
               .options(selectinload(AdvSetting.wb_cabinet))\
               .where(AdvSetting.bidder_active == True)
           result = await session.execute(stmt)
           adv_settings = result.scalars().all()
           for adv_setting in adv_settings:
                wb_cabinet_id = adv_setting.wb_cabinet_id
                if adv_setting.id not in adv_tasks:
                     task = asyncio.create_task((run_bidder_process_for_adv(adv_setting)))
                     adv_tasks[adv_setting.id] = task
                else:
                     if adv_tasks[adv_setting.id].done():
                          logger.debug(f'Задача обновления ставок завершена для кабинета {wb_cabinet_id}')
                          if adv_tasks[adv_setting.id].exception():
                            logger.error(
                                 f'Ошибка обновления ставок: '
                                 f'{adv_tasks[adv_setting.id].exception()},'
                                 f' для кабинета {adv_setting.id}'
                            )

                          del adv_tasks[adv_setting.id]
                await asyncio.sleep(1)
           pass


async def run_bidder_process_for_adv(adv_setting: AdvSetting):
    try:
        await _run_bidder_process_for_adv(adv_setting)
    except Exception as e:
        logger.error(f'Ошибка при обновлении ставок для объявления {adv_setting.adv_id} {e}', exc_info=True)


async def _run_bidder_process_for_adv(adv_setting: AdvSetting):
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    wb_api = WBApi(access)
    step = settings.BIDDER_STEP
    adv_id = adv_setting.adv_id
    async with sm() as session:
        stmt = select(AdvSetting)\
        .where(AdvSetting.adv_id == adv_id)
        result = await session.execute(stmt)
        adv_setting: AdvSetting = result.scalar()
        stmt = select(KeywordSetting)\
        .where(KeywordSetting.adv_setting_id == adv_setting.id,
               KeywordSetting.hard_status == 2)
        result = await session.execute(stmt)
        white_adv_keywords: list[KeywordSetting] = result.scalars().all()
    max_position_for_adv = adv_setting.max_place
    max_cpm = await data_manager.get_max_adv_bid(adv_setting)
    nmid_in_adv = adv_setting.nmids[0]
    promo_positions = []
    cpm_from_parsing = None
    async with  get_clickhouse_client() as client:
        for keyword in white_adv_keywords:
            try:
                _, views, _= await data_manager.get_keyword_statistic_clickhouse(client, keyword.text, adv_id)
            except Exception as e:
                logger.error(f'Ошибка при получении статистики по ключевому слову {keyword.text} {e}')
                continue
            if views == 0:
                continue
            try:
                text = keyword.text
                await parser.add_wb_positions(text, {nmid_in_adv}, 3)
                await redis_manager.set_last_views(adv_id, text, views)
            except Exception as e:
                logger.error(f'Ошибка при получении позиции {e}')
            position = await redis_manager.get_keyword_position(keyword.text, nmid_in_adv)
            if not position:
                continue
            if position.promo_position:
                cpm_from_parsing: int = position.cpm
            promo_position = position.promo_position
            base_position = position.base_position
            if not promo_position and base_position:
                logger.debug('Нет буста')
                continue
            promo_positions.append(position)
            if not cpm_from_parsing:
                cpm_from_parsing = 100
    if promo_positions:
        fact_max_position = max(promo_positions, key=lambda x: x.promo_position)
        promo_position = fact_max_position.promo_position
        if promo_position == 1:
            new_cpm = cpm_from_parsing - step
        elif promo_position < max_position_for_adv:
            new_cpm = cpm_from_parsing - step
        elif promo_position > max_position_for_adv:
            new_cpm = cpm_from_parsing + step
        else:
            new_cpm = cpm_from_parsing

        if new_cpm > max_cpm:
            new_cpm = max_cpm
        if new_cpm == cpm_from_parsing:
            return
        if new_cpm < 100:
            new_cpm = 100
        await wb_api.advert.update_cpm(adv_id, new_cpm)
        if new_cpm < 150:
            new_cpm = 150
        adv_id = adv_setting.search_adv_id
        if adv_id:
            await wb_api.advert.set_search_cpm(adv_id, new_cpm)