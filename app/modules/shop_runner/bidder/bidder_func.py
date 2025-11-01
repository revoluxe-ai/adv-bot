import logging

from dependency_injector.wiring import inject, Provide
import typing
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.core.wb_api.exceptions import ApiForbiddenError
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting, WBItemPosition
from app.modules.shop_runner.bidder.excs import CpmNotFoundError
from app.modules.shop_runner.service_manager.old_modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)
from app.modules.wb_adv_updater import data_manager
from app.modules.wb_keywords_parser.wb_parser import parser
from app.settings import settings
from app.utils import redis_manager
from app.utils.db.session_maker import get_async_session_maker as sm
from ..modules.max_auto_bid_manager.di import AutoMaxCpmContainer

if typing.TYPE_CHECKING:
    from ..modules.max_auto_bid_manager.auto_max_bid_manager import AutoMaxBidManager


from ...common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)

from ..modules.wb_api import WBApi

logger = logging.getLogger(__name__)

# TODO: включить проверку РК: обновлять только если РК активна и не приостановлена


async def get_cpms_from_wb(advs: list[AdvSetting]) -> set[int] | None:
    return {adv.cpm for adv in advs}


async def _update_and_get_advs_from_wb(
    auto_adv: AdvSetting, wb_api: WBApi
) -> list[AuctionAdv]:
    adv_ids = set()
    if auto_adv.bidder_for_auto:
        adv_ids.add(auto_adv.adv_id)
    if search_adv_id := auto_adv.search_adv_id:
        adv_ids.add(search_adv_id)
    if not adv_ids:
        return None
    advs: list[AuctionAdv] = await wb_api.get_advs(list(adv_ids))
    try:
        assert wb_api.access.wb_cabinet is not None
        wb_cabinet_original_id: int = int(wb_api.access.wb_cabinet.id)
        await wb_db_manager.update_advs_in_db(advs, wb_cabinet_original_id)
    except Exception:
        logger.error("Ошибка обновления РК в базе", exc_info=True)
    return advs


@inject
async def run_bidder_process_for_adv(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    auto_max_bid_manager: "AutoMaxBidManager" = Provide[
        AutoMaxCpmContainer.auto_max_cpm_bid_manager
    ],
) -> None:
    adv_id = adv_setting.adv_id
    shop_id = wb_api.shop_id
    advs: list[AuctionAdv] = await _update_and_get_advs_from_wb(adv_setting, wb_api)
    advs_from_wb_with_active_company: list[AuctionAdv] = [
        adv for adv in advs if adv.status_native == "started"
    ]
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
    if adv_setting.auto_max_cpm_mode:
        auto_max_cpm = await auto_max_bid_manager.get_max_cpm(
            adv_setting, keywords, max_cpm
        )
        if auto_max_cpm and auto_max_cpm < max_cpm:
            max_cpm = auto_max_cpm

    step = adv_setting.bidder_step or settings.BIDDER_STEP
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
    nmid = int(adv_setting.nmids[0])

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
        try:
            cpms: set[int] | None = await get_cpms_from_wb(
                advs_from_wb_with_active_company
            )
        except Exception as exc:
            logger.error(
                f"[{shop_id}] [{adv_id}] Ошибка получения ставок", exc_info=True
            )
            raise exc
    except ApiForbiddenError as e:
        raise e
    except Exception:
        logger.error(f"[{shop_id}] [{adv_id}] Ошибка получения ставок", exc_info=True)
        return

    if not cpms:
        logger.error(f"[{shop_id}] [{adv_id}] Не удалось получить ставки")
        return

    try:
        logger.debug(f"[{shop_id}] [{adv_id}] Получение позиции ключа")
        wb_position: WBItemPosition = await redis_manager.get_keyword_position(
            text, nmid
        )
    except Exception:
        logger.error(
            f"[{shop_id}] [{adv_id}] Ошибка получения позиции ключа", exc_info=True
        )
        return

    if not wb_position or wb_position.position is None:
        logger.error(
            f"[{shop_id}] [{adv_id}] Позиция ключа не найдена или нет промопозиции"
        )
        return

    promo_position = wb_position.position
    if promo_position <= max_position or promo_position == 1:
        new_cpm: int = min(cpms) - step
    else:
        new_cpm = max(cpms) + step
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

    logger.debug(f"[{shop_id}] [{adv_id}] Ставки обновлены")
