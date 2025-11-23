import logging

from dependency_injector.wiring import inject, Provide
import typing
from app.core.wb_api.data_classes.advs.auction_adv import AuctionAdv
from app.modules.common_slaves.wildberries import wb_db_manager
from app.modules.common_slaves.wildberries.models import AdvSetting
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
    cpms = {adv.cpm for adv in advs if adv.cpm is not None}
    return cpms if cpms else None


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
    except Exception:  # noqa
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

    if adv_setting.bidder_mode == BidderMode.BY_POSITIONS:
        from ..exceptions import UsersSettingsError
        raise UsersSettingsError('Error in user settings: bidder operation by positions is not supported at the moment')
    elif not adv_setting.bidder_mode or adv_setting.bidder_mode == BidderMode.BY_AUTO_MAX_CPM:
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
    return None
