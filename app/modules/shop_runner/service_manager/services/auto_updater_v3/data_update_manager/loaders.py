"""Загрузчики WB/CH контекста и plan/fact для V3."""

from __future__ import annotations

import logging

from app.modules.predict_keywords_target_place import build_predict_keywords_target_place
from app.modules.predict_keywords_target_place.clickhouse_manager.dto import BidPosition
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import (
    FactData,
)
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.setting_auto_updater import (
    AdvSettingAutoUpdater,
)
from app.modules.shop_runner.service_manager.services.traffic_clicks_manager import (
    TrafficClicksManager,
)
from app.modules.shop_runner.service_manager.wb_shop_data_manager import ComplexAdv
from app.modules.shop_runner.service_manager.wb_shop_data_manager.wb_shop_data_manager import (
    WBShopDataManager,
)
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import (
    CalculatedKeyword,
)
from app.shared.domains.wb.dto.wb_adv_dto import WBAdvDTO

logger = logging.getLogger(__name__)

_WB_ADV_DTO_FACT_LAST_DAYS = 2


async def load_v3_wb_context(
    complex_adv: ComplexAdv,
    *,
    wb_shop_data_manager: WBShopDataManager,
) -> tuple[WBAdvDTO | None, dict[str, list[BidPosition]]]:
    """Один запрос WBAdvDTO + bid profiles на цикл V3 (CH)."""
    if complex_adv.shelf_promotion_active:
        await TrafficClicksManager().enrich(complex_adv)

    wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
    if not wb_dtos:
        return None, {}

    dto = wb_dtos[0]
    nmid = dto.main_nmid
    if dto.search_adv_min_bids.get(nmid) is None:
        logger.warning(
            "[adv_id=%s] v3: min_bid cache miss for nmid=%s, backfill Redis/WB",
            complex_adv.adv_id,
            nmid,
        )
        backfill_ok = await wb_shop_data_manager.backfill_min_bids_for_adv(complex_adv)
        if backfill_ok:
            wb_dtos = await wb_shop_data_manager.get_wb_advs_dto([complex_adv])
            if wb_dtos:
                dto = wb_dtos[0]
        else:
            logger.error(
                "[adv_id=%s] v3: min_bid backfill failed for nmid=%s",
                complex_adv.adv_id,
                nmid,
            )

    predictor = build_predict_keywords_target_place()
    raw_profiles = await predictor.get_keyword_bid_profiles(
        dto, dto.min_target_position
    )
    return dto, raw_profiles


async def resolve_v3_fact_data(
    *,
    dto: WBAdvDTO | None,
    updater: AdvSettingAutoUpdater,
    keywords: list[CalculatedKeyword],
    max_last_period: int,
) -> tuple[FactData, str]:
    """Fact для V3 ladder с Search-leg CPO по spec leg-cpo-economics.

    Orders/method остаются из существующего fact, но pay_for_order для Search
    automation берётся только из explicit Search leg snapshot. Aggregate CPO
    не используется как fallback.
    """
    if (
        isinstance(dto, WBAdvDTO)
        and max_last_period == _WB_ADV_DTO_FACT_LAST_DAYS
    ):
        search_fact = dto.fact.model_copy(
            update={"pay_for_order": dto.search_fact_cpo}
        )
        return search_fact, "dto_search_leg"
    return await updater.get_fact_data(keywords), "updater"
