from dataclasses import dataclass

from app.core.mp.wb.api.adapter.promotion_client.normquery_bids.dto import NormqueryBidDTO
from app.core.mp.wb.dto import AdvMinNmidsBids
from app.modules.shop_runner.service_manager.old_modules.setting_auto_updater.data_classes import PlanData, FactData
from app.modules.shop_runner.service_manager.wb_shop_data_manager.dto.complex_adv import ComplexAdv


@dataclass(frozen=True)
class BidderUpdateData:
    advs: list[ComplexAdv]
    cluster_bids: list[NormqueryBidDTO] | None
    min_bids: AdvMinNmidsBids
    plan_datas: dict[int, PlanData]
    fact_datas: dict[int, FactData]


