from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    BidderCoroutineType,
    BidderMode,
)


@dataclass(frozen=True)
class CampaignDefaultsV1:
    """
    Единая точка дефолтных настроек:
    - для новых кампаний
    - для кнопки 'привести к актуальному состоянию'
    НЕ содержит:
    - денег
    - планов
    - стратегий товара
    """

    # --- БАЗОВАЯ РАБОТА БИДДЕРА ---
    bidder_active: bool = True
    bidder_for_auto: bool = True
    bidder_mode: BidderMode = BidderMode.BY_POSITIONS

    # --- АКТУАЛЬНАЯ АВТОМАТИКА ---
    bidder_coroutine_type: BidderCoroutineType = (
        BidderCoroutineType.UPDATE_CLUSTER_BIDS
    )

    # --- МЕТОДОЛОГИЯ РАСЧЁТОВ ---
    orders_source_for_auto_mode: OrdersSourceForAutoMode = (
        OrdersSourceForAutoMode.COMMON_STATISTIC
    )
    sales_predict_method: FactMethods = FactMethods.BY_CARTS

    # --- АВТОМЕХАНИКА ---
    auto_update_white_list: bool = True
    auto_update_target_place: bool = True
    auto_budget_watchdog_enabled: bool = True
    use_common_budget: bool = True

    # --- LEGACY / SANITATION ---
    target_ctr_mode: bool = False
    new_auto_min_ctr_mode: bool = False
    reset_place: bool = True

    # A/B Hold default «выкл» живёт в CommonModeDefaultsPolicy
    # (openspec/decisions/mode-defaults-policy-ownership); не дублируем здесь.
