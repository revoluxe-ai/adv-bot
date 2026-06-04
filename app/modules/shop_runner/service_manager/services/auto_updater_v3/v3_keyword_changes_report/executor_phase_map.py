"""Маппинг имён executor → phase_id отчёта V3."""

from __future__ import annotations

from app.modules.shop_runner.service_manager.services.auto_updater_v3.v3_tick_report import (
    PHASE_TITLES,
)

EXECUTOR_TO_PHASE_ID: dict[str, str] = {
    "HardStatusValidateExecutor": "validate_state_by_hard_status",
    "NotFullValidateExecutor": "validate_not_full_state",
    "SkipUpTargetPlaceExecutor": "skip_up_same_target_place",
    "RaiseStateToTargetCpoExecutor": "raise_state_to_target_cpo",
    "ResetOverMaxCpoOnOverspendExecutor": "reset_over_max_cpo_on_overspend",
    "ShelfCleanupExecutor": "shelf_cleanup",
    "RebalanceExecutor": "cost_reallocation",
    "PayForOrderGapEnableExecutor": "pay_for_order_gap_enable",
    "ResolveCalibrationExecutor": "resolve_calibration",
}

# Служебные executor — не попадают в отчёт фаз.
IGNORED_EXECUTOR_NAMES: frozenset[str] = frozenset(
    {
        "PrepareExecutor",
        "from_prepared_row",
    }
)

# Короткие метки для цепочки ключa (audit Redis).
EXECUTOR_SHORT_LABEL: dict[str, str] = {
    "HardStatusValidateExecutor": "V",
    "NotFullValidateExecutor": "NF",
    "SkipUpTargetPlaceExecutor": "skip",
    "RaiseStateToTargetCpoExecutor": "R↑",
    "ResetOverMaxCpoOnOverspendExecutor": "R↓",
    "ShelfCleanupExecutor": "S",
    "RebalanceExecutor": "R",
    "PayForOrderGapEnableExecutor": "en",
    "ResolveCalibrationExecutor": "cal",
    "DATA_BOOTSTRAP": "boot",
}


def phase_id_for_executor(executor_name: str) -> str:
    """phase_id для executor; неизвестный → slug от имени класса."""
    mapped = EXECUTOR_TO_PHASE_ID.get(executor_name)
    if mapped is not None:
        return mapped
    return executor_name


def title_ru_for_phase(phase_id: str) -> str:
    """Заголовок фазы из ``PHASE_TITLES`` или fallback."""
    meta = PHASE_TITLES.get(phase_id)
    if meta is None:
        return phase_id
    return meta[0]


def short_label_for_executor(executor_name: str) -> str:
    """Короткая метка executor для audit-цепочки."""
    return EXECUTOR_SHORT_LABEL.get(executor_name, executor_name[:8])
