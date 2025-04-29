import logging

from app.client_bot.const import DEFAULT_BIDDER_STEP
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.bidder.excs import CpmNotFoundError
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from ..bidder.wb_api import WBApi as BidderAPI
from ...common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)

logger = logging.getLogger(__name__)


async def get_cpms_from_wb(auto_adv: AdvSetting, wb_api: BidderAPI) -> set[int] | None:
    adv_ids = []
    if auto_adv.bidder_for_auto:
        adv_ids.append(auto_adv.adv_id)
    if search_adv_id := auto_adv.search_adv_id:
        adv_ids.append(search_adv_id)
    if not adv_ids:
        return None

    advs = await wb_api.get_advs(adv_ids)
    try:
        wb_cabinet_original_id: int = wb_api.access.wb_cabinet.id
        async with sm(read_only=False) as session:
            await wb_db_manager.update_advs_in_db(advs, wb_cabinet_original_id, session)
    except Exception:
        logger.error("Ошибка обновления РК в базе", exc_info=True)

    return {adv.cpm for adv in advs}


async def run_bidder_process_for_adv(
    adv_setting: AdvSetting, wb_api: BidderAPI, keywords: list[CalculatedKeyword]
) -> None:
    adv_id = adv_setting.adv_id
    shop_id = wb_api.shop_id
    try:
        logger.debug(f"[{shop_id}] [{adv_id}] Получение максимальной ставки")
        max_cpm = await data_manager.get_max_adv_bid(adv_setting)
    except CpmNotFoundError:
        logger.error(f"[{shop_id}] [{adv_id}] Максимальная ставка не найдена")
        return
    except Exception:
        logger.error(
            f"[{shop_id}] [{adv_id}] Ошибка при получении максимальной ставки",
            exc_info=True,
        )
        return

    if not max_cpm:
        logger.error(f"[{shop_id}] [{adv_id}] Максимальная ставка не задана!")
        return

    step = adv_setting.bidder_step or DEFAULT_BIDDER_STEP
    max_position = adv_setting.max_place
    if max_position is None:
        logger.error(f"[{shop_id}] [{adv_id}] Максимальная позиция не задана!")
        return

    white_keywords = [kw for kw in keywords if kw.hard_status == 2]
    best_keyword = data_manager.get_best_keyword(white_keywords)

    if not (adv_setting.nmids and best_keyword):
        logger.error(f"[{shop_id}] [{adv_id}] Нет ключа в белом списке или артикулов")
        return

    text = best_keyword.text
    nmid = adv_setting.nmids[0]

    try:
        logger.debug(f"[{shop_id}] [{adv_id}] Парсинг ключа '{text}'")
        await parser.add_wb_positions(text, {nmid}, delay=0.1)
    except Exception:
        logger.error(
            f"[{shop_id}] [{adv_id}] Ошибка парсинга ключа '{text}'", exc_info=True
        )
        return

    try:
        logger.debug(f"[{shop_id}] [{adv_id}] Получение ставок для биддера")
        cpms: set[int] | None = await get_cpms_from_wb(adv_setting, wb_api)
    except Exception:
        logger.error(f"[{shop_id}] [{adv_id}] Ошибка получения ставок", exc_info=True)
        return

    if not cpms:
        logger.error(f"[{shop_id}] [{adv_id}] Не удалось получить ставки")
        return

    try:
        logger.debug(f"[{shop_id}] [{adv_id}] Получение позиции ключа")
        wb_position = await redis_manager.get_keyword_position(text, nmid)
    except Exception:
        logger.error(
            f"[{shop_id}] [{adv_id}] Ошибка получения позиции ключа", exc_info=True
        )
        return

    if not wb_position or wb_position.promo_position is None:
        logger.error(
            f"[{shop_id}] [{adv_id}] Позиция ключа не найдена или нет промопозиции"
        )
        return

    promo_position = wb_position.promo_position
    if promo_position <= max_position or promo_position == 1:
        new_cpm: int = min(cpms) - step
    else:
        new_cpm = max(cpms) + step

    new_cpm = max(min(new_cpm, max_cpm), 125)

    if new_cpm >= max_cpm and adv_setting.reset_place:
        async with sm(read_only=False) as session:
            assert adv_setting
            adv_setting_for_update: AdvSetting | None = await session.get(
                AdvSetting, adv_setting.id
            )
            if adv_setting_for_update is None:
                logger.error(f"[{shop_id}] [{adv_id}] Настройки РК не найдены")
                raise Exception("Настройки РК не найдены")
            adv_setting_for_update.max_place = promo_position + 1
            await session.commit()

    async def update_cpm(
        target_adv_id: int, cpm: int, wb_api_updater: BidderAPI
    ) -> None:
        await wb_api_updater.update_cpm(target_adv_id, cpm)
        await redis_manager.set_last_adv_bid(target_adv_id, cpm)

    async def update_search_cpm(
        target_adv_id: int, cpm: int, wb_api_updater: BidderAPI
    ) -> None:
        await wb_api_updater.set_search_cpm(target_adv_id, cpm)
        await redis_manager.set_last_adv_bid(target_adv_id, cpm)

    if adv_setting.bidder_for_auto:
        auto_adv_id = adv_setting.adv_id
        assert auto_adv_id is not None
        await update_cpm(auto_adv_id, max(new_cpm, 150), wb_api)

    if adv_setting.search_adv_id:
        await update_cpm(adv_setting.search_adv_id, max(new_cpm, 150), wb_api)

    logger.debug(f"[{shop_id}] [{adv_id}] Ставки обновлены")
