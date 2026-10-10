"""
Read-only runtime иерархического контроля (Task 4.1).

Один supplier-orders read на магазин и окно, shop spend из ``full_adv_wb_stat``,
campaign economics только из ``AttributionFactsReader``. Без WB writes, Apply
и headroom allocator.
"""

from app.modules.ad_control_settings.runtime.evaluation import (
    ShopEvaluationResult,
    evaluate_shop_window,
)

__all__ = [
    "ShopEvaluationResult",
    "evaluate_shop_window",
]
