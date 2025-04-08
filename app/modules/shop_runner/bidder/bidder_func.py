from app.client_bot.const import DEFAULT_BIDDER_STEP
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.api import AdvertApi
from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.wb_keywords_parser.wb_parser import parser
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
import logging
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.bidder.excs import CpmNotFoundError
from app.modules.wb_adv_updater import data_manager

logger = logging.getLogger(__name__)


async def get_cpms_from_wb(auto_adv: AdvSetting, wb_api: AdvertApi) -> set[float] | None:
    adv_ids = []
    if auto_adv.bidder_for_auto:
        adv_ids.append(auto_adv.adv_id)
    if search_adv_id := auto_adv.search_adv_id:
        adv_ids.append(search_adv_id)
    if not adv_ids:
        return None
    advs = await wb_api.get_advs(adv_ids)
    wb_cabinet_original_id = int(wb_api.wb_cabinet.id)
    try:
        async with sm(read_only=False) as session:
            await wb_db_manager.update_advs_in_db(advs, wb_cabinet_original_id, session)
    except Exception:
        logger.error('Ошибка обновления РК в базе', exc_info=True)
    cpms = {adv.cpm for adv in advs}
    return cpms


async def run_bidder_process_for_adv(adv_setting: AdvSetting, wb_api: AdvertApi, shop_id: str):
    adv_id = adv_setting.adv_id
    try:
        logger.debug(f'Получаю максимальную ставку для биддера для {shop_id} adv_id {adv_id}')
        max_cpm = await data_manager.get_max_adv_bid(adv_setting)
        logger.debug(f'Максимальная ставка получена для {shop_id} adv_id {adv_id}')
    except CpmNotFoundError:
        logger.error(f'Максимальная ставка не найдена для {shop_id} adv_id {adv_id}')
        return
    except Exception:
        logger.error(f'Ошибка при получении максимальной ставки для {shop_id} adv_id {adv_id}', exc_info=True)
        return

    if not max_cpm:
        logger.error(f'Максимальная ставка не задана для shop_id {shop_id} adv_id {adv_id}!')
        return
    logger.debug(f'Непосредственная задача обновления ставок для магазина {shop_id} adv_id {adv_id} начата')
    step = adv_setting.bidder_step
    if not step:
        step = DEFAULT_BIDDER_STEP
    logger.debug(f'Получил ставку из настроек для {shop_id} adv_id {adv_id}')
    max_position_for_adv = adv_setting.max_place
    if max_position_for_adv is None:
        logger.error(f'Максимальная позиция не задана для {adv_id} adv_id {adv_id} !')
        return

    logger.debug(f'Максимальная ставка получена для {shop_id} adv_id {adv_id}')
    nmid_in_adv = adv_setting.nmids[0]
    logger.debug(f'Получаю ключи для биддера для {shop_id}  adv_id {adv_id}')
    try:
        keywords = await data_manager.get_good_bad_phrases(adv_setting)
        logger.debug(f'Ключи получены для {shop_id}, adv_id {adv_id}')
    except Exception:
        logger.error(f'Ошибка при получении ключей для {shop_id} adv_id {adv_id}', exc_info=True)
        return
    white_keywords: list[CalculatedKeyword] = [kw for kw in keywords if kw.keyword_setting.hard_status == 2]
    best_white_keyword = data_manager.get_best_keyword(white_keywords)
    nmid = adv_setting.nmids[0]
    if best_white_keyword:
        text = best_white_keyword.text
        logger.debug(f'Парсим ключ {text} для {shop_id} adv_id {adv_id}')
        try:
            await parser.add_wb_positions(text, {nmid}, delay=3)
            logger.debug(f'Парсинг ключа {text} успешно завершен для {shop_id} adv_id {adv_id}')
        except Exception as e:
            logger.error(f'Ошибка {e} парсинга ключа {text} для {shop_id} adv_id {adv_id} артикул {nmid}',
                         exc_info=True)
            return
    else:
        logger.error(f'Нет ключа в белом списке для {shop_id}  adv_id: {adv_id}')
        return
    logger.debug(f'Получаю ставку для биддера для {shop_id} adv_id {adv_id}')
    try:
        auto_adv: AdvSetting = adv_setting
        cpms: set[int | float] = await get_cpms_from_wb(auto_adv, wb_api)
    except Exception as e:
        logger.error(f'Ошибка {e} при получении ставки для {shop_id} adv_id {adv_id}', exc_info=True)
        return
    logger.debug(f'Ставка получена для {shop_id} adv_id {adv_id}')
    if not cpms:
        logger.debug(f'Не удалось получить ставку для биддера для кампании {adv_id} для {shop_id}')
        return
    logger.debug(f'Получаю позицию бест ключа из белого списка для {shop_id} adv_id {adv_id}')
    try:
        wb_position = await redis_manager.get_keyword_position(text, nmid_in_adv)
        logger.debug(f'Позиция ключа из белого списка получена для {shop_id} adv_id {adv_id}')
    except Exception as e:
        logger.error(f'Ошибка при получении позиции ключа для {shop_id} adv_id {adv_id}: {e}', exc_info=True)
        return
    if wb_position:
        promo_position = wb_position.promo_position
        if not promo_position:
            logger.error(f'У объекта позиции нет промопозиции shop_id {shop_id} в adv_id: {adv_id}')
            return
        if promo_position < max_position_for_adv or promo_position == 1:
            fact_cmp_for_with_step = min(cpms)
            new_cpm = fact_cmp_for_with_step - step
        elif promo_position > max_position_for_adv:
            fact_cmp_for_with_step = max(cpms)
            new_cpm = fact_cmp_for_with_step + step
        else:
            fact_cmp_for_with_step = min(cpms)
            new_cpm = fact_cmp_for_with_step - step
        if new_cpm >= max_cpm:
            new_cpm = max_cpm
            if adv_setting.reset_place:
                async with sm(read_only=False) as session:
                    adv_setting = await session.get(AdvSetting, adv_setting.id)
                    adv_setting.max_place = promo_position + 1
                    await session.commit()
        if new_cpm < 125:
            new_cpm = 125
        if adv_setting.bidder_for_auto:
            await wb_api.update_cpm(adv_id, new_cpm)
            await redis_manager.set_last_adv_bid(adv_id, new_cpm)
        if new_cpm < 150:
            new_cpm = 150
        adv_id = adv_setting.search_adv_id
        if adv_id:
            await wb_api.set_search_cpm(adv_id, new_cpm)
            await redis_manager.set_last_adv_bid(adv_id, new_cpm)
        logger.debug(f'Ставки для {adv_id} магазина {shop_id} обновлены')
    else:
        logger.error(f'Не найден мастер ключ для биддера для рк {adv_setting.adv_id} shop_id {shop_id}')
        return
