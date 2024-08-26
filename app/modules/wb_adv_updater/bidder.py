import logging

import aiohttp

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
from ...utils import redis_manager
from  app.modules.wb_keywords_parser import parser




logger = logging.getLogger(__name__)



async def run_bidder_process():
    while True:
        try:
            await _run_bidder_process()
        except Exception as e:
            logger.error(f'Ошибка процесса управления ставками {e}', exc_info=True)
        await asyncio.sleep(0)



async def _run_bidder_process():
    wb_cabinet_tasks = {}
    adv_tasks = {}
    while True:
        accesses = super_cabinet_manager.get_accesses_for_bidder()
        logger.debug(f'Получен генератор доступов к кабинетам для биддера')
        async for access in accesses:
            cabinet_id = access.wb_cabinet.id
            if cabinet_id not in wb_cabinet_tasks:
                logger.debug(f'Запуск задачи обновления ставок для кабинета {cabinet_id}')
                task = asyncio.create_task(_run_bidder_process_for_wb_cabinet(access,
                                                                              adv_tasks=adv_tasks))
                wb_cabinet_tasks[cabinet_id] = task

            else:
                if wb_cabinet_tasks[cabinet_id].done():
                    logger.debug(f'Задача обновления обновления ставок {cabinet_id}')
                    if wb_cabinet_tasks[cabinet_id].exception():
                        logger.error(
                            f'Ошибка обновления ставок: '
                            f'{wb_cabinet_tasks[cabinet_id].exception()},'
                            f' для кабинета {cabinet_id}'
                        )

                    del wb_cabinet_tasks[cabinet_id]
        await asyncio.sleep(0)




async def _run_bidder_process_for_wb_cabinet(access: WBCabinetAccess, adv_tasks: dict):
    logger.debug(f'Запуск задачи обновления ставок для кабинета {access.wb_cabinet.id}')
    wb_api = WBApi(access)
    wb_cabinet = access.wb_cabinet
    async with sm() as session:
        stmt = select(AdvSetting) \
            .join(AdvSetting.wb_cabinet) \
            .where(WBCabinet.id == wb_cabinet.id,
                   AdvSetting.bidder_active == True,
                   AdvSetting.bot_active == True,
                   AdvSetting.active_status == 'started')
        result = (await session.execute(stmt)).unique()
        adv_settings = result.scalars().all()
    for adv_setting in adv_settings:
        if adv_setting.id not in adv_tasks:
            task = asyncio.create_task(_run_bidder_process_for_adv(adv_setting.adv_id, wb_api))
            adv_tasks[adv_setting.id] = task
        else:
            if adv_tasks[adv_setting.id].done():
                logger.info(
                    f'Задача управления ставкой завершена для кабинета '
                    f'{adv_setting.name}'
                )
                if adv_tasks[adv_setting.id].exception():
                    logger.error(
                        f'Ошибка обновления статистики ключей: '
                        f'{adv_tasks[adv_setting.id].exception()},'
                        f' для кабинета {adv_setting.name}'
                    )

                del adv_tasks[adv_setting.id]
                logger.info(f'Статистика ключевых слов для {adv_setting.name} обновлена')
                logger.debug(f'Установка set для need_update_model')
    return


async def _run_bidder_process_for_adv(adv_id: int,
                                      wb_api: WBApi):
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
    max_cpm = adv_setting.max_cpm
    nmid_in_adv = adv_setting.nmids[0]
    promo_positions = []
    cpm_from_parsing = None
    for keyword in white_adv_keywords:
        _, views, _= await data_manager.get_keyword_statistic_clickhouse(keyword, adv_id)
        if views == 0:
            continue
        try:
            await parser.add_wb_positions(keyword.text, {nmid_in_adv})
        except Exception as e:
            logger.error(f'Ошибка при получении позиции {e}')
            continue
        position = await redis_manager.get_keyword_position(keyword.text, nmid_in_adv)
        if not position:
            continue
        promo_position = position.promo_position
        base_position = position.base_position
        if not promo_position and base_position:
            logger.debug('Нет буста')
            continue
        promo_positions.append(promo_position)
        cpm_from_parsing: int = position.cpm
        if not cpm_from_parsing:
            cpm_from_parsing = 100
    if promo_positions:
        fact_max_position: int = max(promo_positions)
        if fact_max_position == 1:
            new_cpm = cpm_from_parsing - 1
        elif fact_max_position < max_position_for_adv:
            new_cpm = cpm_from_parsing - 1
        elif fact_max_position > max_position_for_adv:
            new_cpm = cpm_from_parsing + 1
        else:
            new_cpm = cpm_from_parsing

        if new_cpm > max_cpm:
            new_cpm = max_cpm
        elif new_cpm < 100:
            new_cpm = 100
        if new_cpm != cpm_from_parsing:
           await wb_api.advert.update_cpm(adv_id, new_cpm)