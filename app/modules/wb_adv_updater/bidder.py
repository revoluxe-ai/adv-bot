import asyncio
import logging

from sqlalchemy import or_
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.modules.common_slaves.wildberries.models import AdvSetting, WBCabinet
from app.modules.common_slaves.wildberries.wb_api import WBApi
from app.modules.wb_adv_updater import data_manager
from app.utils.db.session_maker import get_async_session_maker as sm

from ...settings import settings
from ..common_slaves.wildberries import super_cabinet_manager
from ..common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


async def _run_bidder_process():
    adv_tasks = {}
    while True:
        async with sm() as session:
            stmt = (
                select(AdvSetting)
                .join(AdvSetting.wb_cabinet)
                .options(selectinload(AdvSetting.wb_cabinet))
                .where(
                    AdvSetting.bidder_active == True,
                    or_(
                        AdvSetting.wb_cabinet.has(WBCabinet.balance > 0),
                        AdvSetting.wb_cabinet.has(WBCabinet.bonus > 0),
                    ),
                )
            )
            result = await session.execute(stmt)
            adv_settings = result.scalars().all()
            for adv_setting in adv_settings:
                wb_cabinet_id = adv_setting.wb_cabinet_id
                if adv_setting.id not in adv_tasks:
                    task = asyncio.create_task(run_bidder_process_for_adv(adv_setting))
                    adv_tasks[adv_setting.id] = task
                else:
                    if adv_tasks[adv_setting.id].done():
                        logger.debug(
                            f"Задача обновления ставок завершена для кабинета {wb_cabinet_id}"
                        )
                        if adv_tasks[adv_setting.id].exception():
                            logger.error(
                                f"Ошибка обновления ставок: "
                                f"{adv_tasks[adv_setting.id].exception()},"
                                f" для кабинета {adv_setting.id}"
                            )

                        del adv_tasks[adv_setting.id]
                await asyncio.sleep(1)
            pass


async def run_bidder_process_for_adv(adv_setting: AdvSetting):
    try:
        await _run_bidder_process_for_adv(adv_setting)
    except Exception as e:
        logger.error(
            f"Ошибка при обновлении ставок для объявления {adv_setting.adv_id} {e}",
            exc_info=True,
        )


async def _run_bidder_process_for_adv(adv_setting: AdvSetting):
    wb_cabinet_id = adv_setting.wb_cabinet_id
    access = await super_cabinet_manager.get_access_for_wb_cabinet(wb_cabinet_id)
    wb_api = WBApi(access)
    step = settings.BIDDER_STEP
    adv_id = adv_setting.adv_id
    max_position_for_adv = adv_setting.max_place
    if max_position_for_adv is None:
        logger.error("Максимальная позиция не задана!")
        return
    max_cpm = await data_manager.get_max_adv_bid(adv_setting)
    keywords = await data_manager.get_good_bad_phrases(adv_setting)
    fact_cpm = await data_manager.get_cpm(adv_setting, keywords)
    if not fact_cpm:
        logger.error(
            "Не удалось получить ставку из парсинга"
            f"Shop ID: {access.wb_cabinet.shop_id}"
            f"Adv ID: {adv_id}",
            exc_info=True,
        )
        return
    white_keywords: list[CalculatedKeyword] = [
        kw for kw in keywords if kw.hard_status == 2
    ]
    best_white_keyword = data_manager.get_best_keyword(white_keywords)
    if best_white_keyword:
        promo_position = best_white_keyword.position
    else:
        promo_position = None
    if promo_position:
        if promo_position < max_position_for_adv:
            new_cpm = fact_cpm - step
        elif promo_position > max_position_for_adv:
            new_cpm = fact_cpm + step
        else:
            new_cpm = fact_cpm
        if not max_cpm:
            logger.error("Максимальная ставка не задана!")
            return
        if new_cpm >= max_cpm:
            new_cpm = max_cpm
            if adv_setting.reset_place:
                async with sm(read_only=False) as session:
                    adv_setting = await session.get(AdvSetting, adv_setting.id)
                    adv_setting.max_place = promo_position + 1
                    await session.commit()
        if new_cpm == fact_cpm:
            return
        if new_cpm < 125:
            new_cpm = 125
        await wb_api.advert.update_cpm(adv_id, new_cpm)
        if new_cpm < 250:
            new_cpm = 250
        adv_id = adv_setting.search_adv_id
        if adv_id:
            await wb_api.advert.set_search_cpm(adv_id, new_cpm)
