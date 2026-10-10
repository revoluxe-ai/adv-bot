"""Shop DRR и headroom из целого GMV и shop spend одного окна."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.ad_control_settings.domain.enums import DataSufficiency
from app.modules.ad_control_settings.domain.reason_codes import AdControlReasonCode
from app.modules.ad_control_settings.runtime.money import quantize_percent, quantize_rub
from app.modules.ad_control_settings.runtime.shop_order_gmv import (
    ShopOrderGmvAggregate,
    ShopOrderGmvStatus,
    V1_REVENUE_BASIS,
)
from app.modules.attribution_facts.domain.models import DateWindow


@dataclass(frozen=True, slots=True)
class ShopFactualEconomics:
    """Числовой shop DRR/headroom только при достаточном окне."""

    actual_drr_percent: Decimal | None
    allowed_spend_rub: Decimal | None
    headroom_rub: Decimal | None
    spend_rub: Decimal | None
    gmv_rub: Decimal | None
    sufficiency: DataSufficiency
    reason_codes: tuple[AdControlReasonCode, ...]
    blockers: tuple[str, ...]


def shop_factual_economics(
    gmv: ShopOrderGmvAggregate,
    *,
    spend_rub: Decimal | None,
    spend_window: DateWindow | None,
    shop_target_drr_percent: Decimal | None,
) -> ShopFactualEconomics:
    """
    ``shop_actual_drr = spend / whole_shop_order_gmv`` за одно окно.

    Нулевой GMV не делит: sufficiency INSUFFICIENT, без числового DRR.
    """
    reasons: list[AdControlReasonCode] = []
    blockers: list[str] = []
    if gmv.revenue_basis != V1_REVENUE_BASIS or (
        gmv.reason == AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED
    ):
        reasons.append(AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED)
        return _empty(
            DataSufficiency.UNSUPPORTED,
            reasons,
            ("revenue_basis_unsupported",),
        )
    if spend_window is None or spend_window != gmv.window:
        reasons.append(AdControlReasonCode.CPO_INPUTS_INCOMPLETE)
        blockers.append("window_mismatch")
    if gmv.status == ShopOrderGmvStatus.STALE or (
        gmv.reason == AdControlReasonCode.SHOP_ORDER_GMV_STALE
    ):
        reasons.append(AdControlReasonCode.SHOP_ORDER_GMV_STALE)
    elif gmv.status == ShopOrderGmvStatus.FIELD_ABSENT or (
        gmv.reason == AdControlReasonCode.SHOP_ORDER_GMV_FIELD_ABSENT
    ):
        reasons.append(AdControlReasonCode.SHOP_ORDER_GMV_FIELD_ABSENT)
    elif gmv.status != ShopOrderGmvStatus.COMPLETE or gmv.whole_shop_order_gmv_rub is None:
        reasons.append(
            gmv.reason or AdControlReasonCode.SHOP_ORDER_GMV_INCOMPLETE
        )
    if spend_rub is None:
        reasons.append(AdControlReasonCode.SHOP_SPEND_INCOMPLETE)
        blockers.append("shop_spend_incomplete")
    if shop_target_drr_percent is None:
        reasons.append(AdControlReasonCode.CPO_INPUTS_INCOMPLETE)
        blockers.append("shop_target_missing")
    if reasons:
        sufficiency = (
            DataSufficiency.STALE
            if AdControlReasonCode.SHOP_ORDER_GMV_STALE in reasons
            and AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED not in reasons
            else DataSufficiency.INSUFFICIENT
        )
        if AdControlReasonCode.REVENUE_BASIS_UNSUPPORTED in reasons:
            sufficiency = DataSufficiency.UNSUPPORTED
        return _empty(sufficiency, reasons, tuple(blockers))
    assert gmv.whole_shop_order_gmv_rub is not None
    assert spend_rub is not None
    assert shop_target_drr_percent is not None
    if gmv.whole_shop_order_gmv_rub == 0:
        return _empty(
            DataSufficiency.INSUFFICIENT,
            (AdControlReasonCode.ACTUAL_DRR_INSUFFICIENT,),
            ("zero_shop_order_gmv",),
        )
    spend_q = quantize_rub(spend_rub)
    allowed = quantize_rub(
        gmv.whole_shop_order_gmv_rub * shop_target_drr_percent / Decimal(100)
    )
    actual = quantize_percent(spend_q / gmv.whole_shop_order_gmv_rub * Decimal(100))
    return ShopFactualEconomics(
        actual_drr_percent=actual,
        allowed_spend_rub=allowed,
        headroom_rub=quantize_rub(allowed - spend_q),
        spend_rub=spend_q,
        gmv_rub=gmv.whole_shop_order_gmv_rub,
        sufficiency=DataSufficiency.SUFFICIENT,
        reason_codes=(),
        blockers=(),
    )


def _empty(
    sufficiency: DataSufficiency,
    reasons: tuple[AdControlReasonCode, ...] | list[AdControlReasonCode],
    blockers: tuple[str, ...],
) -> ShopFactualEconomics:
    unique = tuple(dict.fromkeys(reasons))
    return ShopFactualEconomics(
        actual_drr_percent=None,
        allowed_spend_rub=None,
        headroom_rub=None,
        spend_rub=None,
        gmv_rub=None,
        sufficiency=sufficiency,
        reason_codes=unique,
        blockers=blockers,
    )
