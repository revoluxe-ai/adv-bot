from app import settings
from app.modules.common_slaves.wildberries.super_cabinet_manager import WBCabinetAccess
from app.modules.wb_keywords_parser import parser
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
import logging

from app.core.wb_api.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.shop_runner.bidder.wb_api import WBApi
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.bidder.excs import CpmNotFoundError
from app.modules.wb_adv_updater import data_manager

logger = logging.getLogger(__name__)


async def run_bidder_process_for_adv(adv_setting: AdvSetting, wb_api: WBApi):
    step = settings.BIDDER_STEP
    adv_id = adv_setting.adv_id
    max_position_for_adv = adv_setting.max_place
    if max_position_for_adv is None:
        logger.error('Максимальная позиция не задана!')
        return
    max_cpm = await data_manager.get_max_adv_bid(adv_setting)
    nmid_in_adv = adv_setting.nmids[0]
    keywords = await data_manager.get_good_bad_phrases(adv_setting)
    white_keywords: list[CalculatedKeyword] = [kw for kw in keywords if kw.keyword_setting.hard_status == 2]
    best_white_keyword = data_manager.get_best_keyword(white_keywords)
    if best_white_keyword:
        text = best_white_keyword.text
        logger.debug('Парсим ключ')
        await parser.limited_add_wb_positions(text,
                                              {nmid_in_adv},
                                            best_white_keyword.views,
                                              adv_id,
                                              60)
        logger.debug('Парсинг ключа успешно завершен')
    else:
        logger.error('Нет ключа в белом списке')
        return
    cpm_from_parsing = await data_manager.get_cpm_by_nmid(nmid_in_adv)
    if not cpm_from_parsing:
        logger.error(f'Не удалось получить ставку для биддера для кампании {adv_id}')
        return
    logger.debug('Получаю позицию бест ключа из белого списка')
    wb_position = await redis_manager.get_keyword_position(text, nmid_in_adv)
    logger.debug('Позиция ключа из белого списка получена')
    if wb_position:
        promo_position = wb_position.promo_position
        if promo_position < max_position_for_adv:
            new_cpm = cpm_from_parsing - step
        elif promo_position > max_position_for_adv:
            new_cpm = cpm_from_parsing + step
        else:
            new_cpm = cpm_from_parsing
        if not max_cpm:
            logger.error('Максимальная ставка не задана!')
            return
        if new_cpm >= max_cpm:
            new_cpm = max_cpm
            if adv_setting.reset_place:
                async with sm(read_only=False) as session:
                    adv_setting = await session.get(AdvSetting, adv_setting.id)
                    adv_setting.max_place = promo_position + 1
                    await session.commit()
        if new_cpm == cpm_from_parsing:
            logger.debug('Новая ставка равна старой')
            return
        if new_cpm < 125:
            new_cpm = 125
        await wb_api.update_cpm(adv_id, new_cpm)
        if new_cpm < 150:
            new_cpm = 150
        adv_id = adv_setting.search_adv_id
        if adv_id:
            await wb_api.set_search_cpm(adv_id, new_cpm)
        logger.debug(f'Ставки для {adv_id} обновлены')
    else:
        logger.error(f'Не найден мастер ключ для биддера для рк {adv_setting.adv_id}')
        return
