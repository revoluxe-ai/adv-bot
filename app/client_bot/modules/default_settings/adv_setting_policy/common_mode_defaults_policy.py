"""Common campaign defaults independent from FREE/PAID mode."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.enums import OrdersSourceForAutoMode
from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods
from app.modules.common_slaves.wildberries.models.models import (
    AdvSetting,
    BidderCoroutineType,
    BidderMode,
)

from .base_policy import AdvSettingDefaultsPolicy
from .field_policy import FieldPolicy


class CommonCampaignDefaultsPolicy(AdvSettingDefaultsPolicy):
    """Common campaign defaults independent from FREE/PAID mode."""

    name = "common_campaign_defaults"

    rules = (

        FieldPolicy(
            field=AdvSetting.bidder_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: BidderMode.BY_POSITIONS,
            reason="Базовый режим управления ставками.",
        ),
        FieldPolicy(
            field=AdvSetting.bidder_coroutine_type,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: BidderCoroutineType.UPDATE_CLUSTER_BIDS,
            reason="Актуальный live-path bidder.",
        ),
        FieldPolicy(
            field=AdvSetting.orders_source_for_auto_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: OrdersSourceForAutoMode.COMMON_STATISTIC,
            reason="Базовый источник заказов.",
        ),
        FieldPolicy(
            field=AdvSetting.sales_predict_method,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: FactMethods.BY_CARTS,
            reason="Базовый метод прогноза.",
        ),
        FieldPolicy(
            field=AdvSetting.auto_budget_watchdog_enabled,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: True,
            reason="Контроль бюджета.",
        ),

        FieldPolicy(
            field=AdvSetting.use_common_budget,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: True,
            reason="Использовать общий бюджет по текущей дефолтной модели.",
        ),
        FieldPolicy(
            field=AdvSetting.target_ctr_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Legacy/санитация.", # TODO: Надо это вредрить, а то без него free-версия вообще не понятно для чего нужна. Также ограничения по ключам другого вида
        ),
        FieldPolicy(
            field=AdvSetting.new_auto_min_ctr_mode,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: False,
            reason="Legacy/санитация.",
        ),
        FieldPolicy(
            field=AdvSetting.reset_place,
            apply_if=lambda adv, wb_cabinet: True,
            value=lambda adv, wb_cabinet: True,
            reason="Legacy/санитация.",
        ),
        FieldPolicy(
            field=AdvSetting.max_place,
            apply_if=lambda adv, wb_cabinet: adv.max_place is None,
            value=lambda adv, wb_cabinet: 1,
            reason="Не перетираем пользовательскую целевую позицию; если пусто, ставим 1.",
        ),
        FieldPolicy(
            field=AdvSetting.max_cpm,
            apply_if=lambda adv, wb_cabinet: adv.max_cpm is None,
            value=lambda adv, wb_cabinet: wb_cabinet.default_max_cpm,
            reason="Не перетираем пользовательскую max CPM; если пусто, берём дефолт кабинета.",
        ),
    )
