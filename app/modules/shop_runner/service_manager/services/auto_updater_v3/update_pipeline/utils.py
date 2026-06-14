"""Утилиты preamble pipeline: потолок CPO при overspend."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.keyword_dto import (
    UpdateContext,
)


def get_raise_celling(context: UpdateContext) -> float:
    """Per-key потолок trim при overspend: ``max(plan.max, fact)`` (= ``fact`` если overspend)."""
    adv = context.adv_state
    return max(
        float(adv.max_pay_for_order),
        float(adv.fact_pay_for_order),  # type: ignore[arg-type]
    )
