"""Подписи и краткие сводки payload для Telegram-экрана рекламного контроля."""

from __future__ import annotations

from decimal import Decimal

from app.modules.ad_control_settings.domain.configured import (
    ConfiguredFeaturePayload,
    CpoDecreaseOnOverspendParamsV1,
    CpoIncreaseOnHeadroomParamsV1,
    DrrPolicyParamsV1,
    DynamicDrrControlParamsV1,
)
from app.modules.ad_control_settings.domain.enums import AdControlFeatureId

FEATURE_LABELS: dict[AdControlFeatureId, str] = {
    AdControlFeatureId.DRR_POLICY: "Политика DRR",
    AdControlFeatureId.DYNAMIC_DRR_CONTROL: "Динамический DRR",
    AdControlFeatureId.CPO_INCREASE_ON_HEADROOM: "Рост CPO при запасе",
    AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND: "Снижение CPO при перерасходе",
    AdControlFeatureId.CPO_SAFETY_BOUNDS: "Границы CPO",
}

FEATURE_CODES: dict[str, AdControlFeatureId] = {
    "dp": AdControlFeatureId.DRR_POLICY,
    "dd": AdControlFeatureId.DYNAMIC_DRR_CONTROL,
    "ci": AdControlFeatureId.CPO_INCREASE_ON_HEADROOM,
    "cd": AdControlFeatureId.CPO_DECREASE_ON_OVERSPEND,
    "cs": AdControlFeatureId.CPO_SAFETY_BOUNDS,
}

CODE_BY_FEATURE: dict[AdControlFeatureId, str] = {
    feature_id: code for code, feature_id in FEATURE_CODES.items()
}


def feature_label(feature_id: AdControlFeatureId) -> str:
    """Человекочитаемое имя feature из фиксированного словаря UI."""
    return FEATURE_LABELS[feature_id]


def feature_from_code(code: str) -> AdControlFeatureId | None:
    """Короткий callback-код → feature. Неизвестный код → None (fail closed)."""
    return FEATURE_CODES.get(code)


def _dec(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return format(value, "f")


def summarize_payload(payload: ConfiguredFeaturePayload | None) -> str:
    """Сводка configured/effective payload. Не считает DRR, headroom или CPO."""
    if payload is None:
        return "—"
    if isinstance(payload, DrrPolicyParamsV1):
        profile = payload.profile
        return (
            f"target {_dec(profile.target_drr_percent)}% / "
            f"max {_dec(profile.max_drr_percent)}%"
        )
    if isinstance(payload, DynamicDrrControlParamsV1):
        state = "on" if payload.enabled else "off"
        return f"{state}, delta {_dec(payload.max_effective_delta_percent)}%"
    if isinstance(payload, CpoIncreaseOnHeadroomParamsV1):
        return (
            f"min_headroom {_dec(payload.minimum_headroom_rub)} "
            f"step {_dec(payload.maximum_increase_per_iteration_rub)} "
            f"cooldown {payload.cooldown_ticks}"
        )
    if isinstance(payload, CpoDecreaseOnOverspendParamsV1):
        return (
            f"step {_dec(payload.maximum_decrease_per_iteration_rub)} "
            f"cooldown {payload.cooldown_ticks}"
        )
    return (
        f"min {_dec(payload.absolute_min_cpo_rub)} "
        f"max {_dec(payload.absolute_max_cpo_rub)} "
        f"up {_dec(payload.max_step_up_rub)} "
        f"down {_dec(payload.max_step_down_rub)}"
    )
