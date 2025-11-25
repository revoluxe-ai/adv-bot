import logging

from dependency_injector.wiring import inject, Provide
import typing
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.old_modules.adv_common_parameters_manager.adv_parameter_manager import (
    AdvParameterManager,
)

from app.settings import settings

from app.utils.db.session_maker import get_async_session_maker as sm
from .redis_cache.last_keyword_stamp_timestamp_cache import LastKeywordStampTimestampCache

from ..modules.max_auto_bid_manager.di import AutoMaxCpmContainer
from ...common_slaves.wildberries.models.bidder_mode import BidderMode
from ...wb_adv_updater import data_manager

if typing.TYPE_CHECKING:
    from ..modules.max_auto_bid_manager.auto_max_bid_manager import AutoMaxBidManager
    from app.modules.shop_runner.bidder.redis_cache.redis_last_total_views import RedisLastTotalViews


from ...common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)

from ..modules.wb_api import WBApi

logger = logging.getLogger(__name__)

# TODO: включить проверку РК: обновлять только если РК активна и не приостановлена


async def get_cpms_from_wb(advs: list[AuctionAdv]) -> set[int] | None:
    cpms = {adv.cpm for adv in advs if adv.cpm is not None}
    return cpms if cpms else None


async def _update_and_get_advs_from_wb(
    auto_adv: AdvSetting, wb_api: WBApi
) -> list[AuctionAdv]:
    adv_ids: set[int] = set()
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
    except Exception:  # noqa
        logger.error("Ошибка обновления РК в базе", exc_info=True)
    return advs


@inject
async def __get_new_cpm_by_position(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    best_keyword: CalculatedKeyword,
    cpm_now: int,
    auto_max_bid_manager: "AutoMaxBidManager" = Provide[
        AutoMaxCpmContainer.auto_max_cpm_bid_manager
    ],
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

        if auto_max_cpm < max_user_cpm:
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

    promo_position: int | None = best_keyword.position
    if promo_position is None:
        return None
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


@inject
async def run_bidder_process_for_adv(
    adv_setting: AdvSetting,
    wb_api: WBApi,
    keywords: list[CalculatedKeyword],
    auto_max_bid_manager: "AutoMaxBidManager" = Provide[
        AutoMaxCpmContainer.auto_max_cpm_bid_manager
    ],
    redis_last_total_views: "RedisLastTotalViews" = Provide[
        "module_resources.bidder_container.redis_last_total_views"
    ],
      last_keyword_stamp_timestamp_cache: LastKeywordStampTimestampCache = Provide[
          "module_resources.bidder_container.last_keyword_stamp_timestamp_cache"
      ]


) -> None:
    advs: list[AuctionAdv] = await _update_and_get_advs_from_wb(adv_setting, wb_api)
    advs_from_wb_with_active_company: list[AuctionAdv] = [
        adv for adv in advs if adv.status_native == "started"
    ]

    cpms: set[int] | None = await get_cpms_from_wb(advs_from_wb_with_active_company)
    cpm_now = max(cpms) if cpms else None
    if not cpm_now:
        logger.debug(
            "Не удалось определить текущую ставку для shop_id: %s, adv_id: %s",
            wb_api.shop_id,
            adv_setting.adv_id,
        )
        return None

    user_max_cpm = adv_setting.max_cpm
    if not user_max_cpm:
        return None
    white_list = [kw for kw in keywords if kw.hard_status == 2]
    best_keyword = data_manager.get_best_keyword(white_list)
    if not best_keyword:
        return None

    # TODO: Надо тут перепроверить логику выбора режима, включая что по умолчанию в модели и т.д.

    if adv_setting.bidder_mode in [BidderMode.BY_POSITIONS, None]:
        last_views = await redis_last_total_views.get(best_keyword)
        if last_views and last_views > 0 and last_views == best_keyword.total_views:
            return None

        last_time_stamp = await last_keyword_stamp_timestamp_cache.get(best_keyword)
        if last_time_stamp and last_time_stamp == best_keyword.position_update:
            return None
        new_cpm = await __get_new_cpm_by_position(
            adv_setting,
            wb_api,
            keywords,
            best_keyword,
            cpm_now,
        )
        if not new_cpm:
            return None
    elif adv_setting.bidder_mode == BidderMode.BY_AUTO_MAX_CPM:
        if not adv_setting.auto_max_cpm_mode:
            return None
        max_cpm = await auto_max_bid_manager.get_max_cpm(
            adv_setting, keywords, user_max_cpm
        )
        if not max_cpm:
            return None
        new_cpm = max_cpm
    else:
        raise RuntimeError("Неверный режим биддера")

    if not adv_setting.nmids:
        raise RuntimeError("Пустой список nmids - это недопустимое состояние")

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
        # TODO: Вынести в общий код проверку режима биддера
        if adv_setting.bidder_mode in [BidderMode.BY_POSITIONS, None]:
            await redis_last_total_views.set(best_keyword)
            await last_keyword_stamp_timestamp_cache.set(best_keyword)
    return None
