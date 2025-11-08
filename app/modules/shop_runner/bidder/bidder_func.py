import logging

from dependency_injector.wiring import inject, Provide
import typing
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.modules.shop_runner.service_manager.old_modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)

from app.modules.wb_keywords_parser.wb_parser import parser
from app.settings import settings
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from ..modules.max_auto_bid_manager.di import AutoMaxCpmContainer
from ...common_slaves.wildberries.models.bidder_mode import BidderMode

if typing.TYPE_CHECKING:
    from ..modules.max_auto_bid_manager.auto_max_bid_manager import AutoMaxBidManager


from ...common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)

from ..modules.wb_api import WBApi

logger = logging.getLogger(__name__)

# TODO: включить проверку РК: обновлять только если РК активна и не приостановлена


async def get_cpms_from_wb(advs: list[AuctionAdv]) -> set[int] | None:
    return {adv.cpm for adv in advs if adv.cpm}


async def _update_and_get_advs_from_wb(
    auto_adv: AdvSetting, wb_api: WBApi
) -> list[AuctionAdv]:
    adv_ids = set()
    if auto_adv.bidder_for_auto:
        adv_ids.add(auto_adv.adv_id)
    if search_adv_id := auto_adv.search_adv_id:
        adv_ids.add(search_adv_id)
    if not adv_ids:
        return []
    advs: list[AuctionAdv] = await wb_api.get_advs(list(adv_ids))
    try:
        assert wb_api.access.wb_cabinet is not None
        wb_cabinet_original_id: int = int(wb_api.access.wb_cabinet.id)
        await wb_db_manager.update_advs_in_db(advs, wb_cabinet_original_id)
    except Exception: # noqa
        logger.error("Ошибка обновления РК в базе", exc_info=True)
    return advs

@inject
async def __get_new_cpm_by_position(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    cpm_now: int,
    auto_max_bid_manager: "AutoMaxBidManager" = Provide
    [AutoMaxCpmContainer.auto_max_cpm_bid_manager],

) -> int | None:
    adv_id = adv_setting.adv_id
    shop_id = wb_api.shop_id

    max_user_cpm = adv_setting.max_cpm
    if adv_setting.auto_max_cpm_mode:
        auto_max_cpm = await auto_max_bid_manager.get_max_cpm(
            adv_setting, keywords, max_user_cpm
        )
        if not auto_max_cpm:
            return None

        if  auto_max_cpm < max_user_cpm:
            max_cpm = auto_max_cpm
        else:
            max_cpm = max_user_cpm
    else:
        max_cpm = max_user_cpm
    step = adv_setting.bidder_step or settings.BIDDER_STEP
    max_position = adv_setting.max_place
    if max_position is None:
        logger.error(f"[{shop_id}] [{adv_id}] Максимальная позиция не задана!")
        return None
    
    white_keywords = [kw for kw in keywords if kw.hard_status == 2]
    if not white_keywords:
        logger.warning("[%s] [%s ] Нет ключей в белом списке", shop_id, adv_id)
        return None
    for keyword in keywords:
        text = keyword.text
        nmid = int(adv_setting.nmids[0])
        try:
            logger.debug(f"[{shop_id}] [{adv_id}] Парсинг ключа '{text}'")
            _: list[WBItemPosition] = await parser.add_wb_positions(text, {nmid}, delay=1)
        except Exception:  # noqa
            logger.error(
                f"[{shop_id}] [{adv_id}] Ошибка парсинга ключа '{text}'", exc_info=True
            )
            continue
    
        try:
            logger.debug(f"[{shop_id}] [{adv_id}] Получение позиции ключа")
            wb_position: WBItemPosition = await redis_manager.get_keyword_position(
                text, nmid
            )
        except Exception:  # noqa
            logger.error(
                f"[{shop_id}] [{adv_id}] Ошибка получения позиции ключа", exc_info=True
            )
            continue
    
        if not wb_position or wb_position.position is None:
            logger.error(
                f"[{shop_id}] [{adv_id}] Позиция ключа не найдена или нет промопозиции"
            )
            continue
        promo_position: int = wb_position.position
        if promo_position == -1:
            continue
        if 0 < promo_position <= max_position:
            new_cpm: int = cpm_now - step
        else:
            new_cpm = cpm_now + step
        adv_param_manager = AdvParameterManager()
        min_cpm = await adv_param_manager.get_min_cpm(adv_setting)
        new_cpm = max(min(new_cpm, max_cpm), min_cpm)
    
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

        logger.debug(f"[{shop_id}] [{adv_id}] Ставки обновлены")
        return new_cpm
    return None


@inject
async def run_bidder_process_for_adv(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    auto_max_bid_manager: "AutoMaxBidManager" = Provide
    [AutoMaxCpmContainer.auto_max_cpm_bid_manager]
) -> None:
    advs: list[AuctionAdv] = await _update_and_get_advs_from_wb(adv_setting, wb_api)
    advs_from_wb_with_active_company: list[AuctionAdv] = [
        adv for adv in advs if adv.status_native == "started"
    ]
 
    cpms: set[int] | None = await get_cpms_from_wb(
        advs_from_wb_with_active_company
    )
    cpm_now = max(cpms) if cpms else None
    if not cpm_now:
        logger.error('Не удалось определить текущую ставку для shop_id: %s, adv_id: %s',
                     wb_api.shop_id, adv_setting.adv_id)
        return None


    user_max_cpm = adv_setting.max_cpm
    if not user_max_cpm:
        return None

    if adv_setting.bidder_mode == BidderMode.BY_POSITIONS:
        new_cpm = await __get_new_cpm_by_position(adv_setting,
                                                  wb_api,
                                                  keywords,
                                                  cpm_now,
                                                )
        if not new_cpm:
            return None
    elif adv_setting.bidder_mode == BidderMode.BY_AUTO_MAX_CPM:
        if not adv_setting.auto_max_cpm_mode:
            return None
        max_cpm = await auto_max_bid_manager.get_max_cpm(adv_setting, keywords, user_max_cpm)
        if not max_cpm:
            return None
        new_cpm = max_cpm
    else:
        raise RuntimeError('Неверный режим биддера')
    
    nmid = adv_setting.nmids[0]
    
    if new_cpm != cpm_now:
        if adv_setting.bidder_for_auto:
            auto_adv_id = int(adv_setting.adv_id)
            assert auto_adv_id is not None
            await wb_api.update_cpm(
                auto_adv_id,
                nmid,
                new_cpm,
            )

        if adv_setting.search_adv_id:
            await wb_api.update_cpm(
                adv_setting.search_adv_id,
                nmid,
                new_cpm,
            )
    return None
