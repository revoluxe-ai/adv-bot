"""Политика мутаций bounded-операций ChangeSetV1.

Excel ``editable`` не выдаёт право менять поле. Нормализация зарегистрированных
settings-полей делегируется ``campaign_settings_contract.normalize_value``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.modules.campaign_settings_contract import (
    REGISTERED_SOURCES,
    CanonicalizationError,
    normalize_value,
)

_REGISTRY_SOURCE = "AdvSetting"

KNOWN_CAPABILITIES: frozenset[str] = frozenset(
    {
        "campaign.set_budget_policy",
        "campaign.set_sales_policy",
        "campaign.set_bid_control_policy",
    }
)

BUDGET_FIELDS: tuple[str, ...] = (
    "auto_budget_watchdog_enabled",
    "auto_budget_daily_limit",
    "search_auto_budget_daily_limit",
    "use_common_budget",
    "common_budget_daily_limit",
    "auto_budget_total_limit",
    "search_auto_budget_total_limit",
    "common_budget_total_limit",
)

SALES_FIELDS: tuple[str, ...] = (
    "orders_source_for_auto_mode",
    "plan_for_sales_for_day",
    "target_price_for_order",
    "max_price_for_order",
    "sales_predict_method",
    "strategy",
    "auto_update_strategy",
)

BID_CONTROL_FIELDS: tuple[str, ...] = (
    "auto_shelf_bid_control_enabled",
    "auto_shelf_bid_control_strategy",
)


@dataclass(frozen=True, slots=True)
class OperationMutationPolicy:
    """Мутабельность одной bounded-операции.

    ``domain_validators`` — имена инвариантов. Имя без реализации отклоняет
    весь ChangeSet (fail closed), а не пропускает проверку.
    """

    operation: str
    bucket: str
    fields: tuple[str, ...]
    required_capability: str
    domain_validators: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NormalizationFailure:
    """Нормализация или allowlist поля не прошли. Записи не происходит."""

    code: str
    message: str


OPERATION_POLICIES: dict[str, OperationMutationPolicy] = {
    "campaign.set_budget_policy": OperationMutationPolicy(
        operation="campaign.set_budget_policy",
        bucket="budget",
        fields=BUDGET_FIELDS,
        required_capability="campaign.set_budget_policy",
        domain_validators=("non_negative_limits",),
    ),
    "campaign.set_sales_policy": OperationMutationPolicy(
        operation="campaign.set_sales_policy",
        bucket="sales",
        fields=SALES_FIELDS,
        required_capability="campaign.set_sales_policy",
        domain_validators=("non_negative_limits", "sales_target_not_above_max"),
    ),
    "campaign.set_bid_control_policy": OperationMutationPolicy(
        operation="campaign.set_bid_control_policy",
        bucket="bid_control",
        fields=BID_CONTROL_FIELDS,
        required_capability="campaign.set_bid_control_policy",
        domain_validators=("bid_control_enabled_requires_strategy",),
    ),
}


def policy_for(operation: str) -> OperationMutationPolicy | None:
    """Политика операции или None, если операция вне bounded-набора."""
    return OPERATION_POLICIES.get(operation)


def normalize_registered_value(
    field_name: str,
    value: object,
) -> tuple[object, NormalizationFailure | None]:
    """Нормализовать поле реестра AdvSetting через ``normalize_value``.

    Неизвестное поле реестра и значение вне типа или allowlist — отказ.
    ``None`` остаётся ``None`` (явная очистка), без подстановки default.
    """
    policy = REGISTERED_SOURCES[_REGISTRY_SOURCE].fields.get(field_name)
    if policy is None:
        return None, NormalizationFailure(
            code="UNKNOWN_FIELD_MAPPING",
            message=f"field {field_name} has no campaign settings mapping",
        )
    if value is None:
        return None, None
    try:
        normalized: object = normalize_value(policy.normalization, value)
    except CanonicalizationError as exc:
        return None, NormalizationFailure(
            code="INVALID_VALUE",
            message=str(exc),
        )
    allowed = policy.allowed_values
    if allowed and (not isinstance(normalized, str) or normalized not in allowed):
        return None, NormalizationFailure(
            code="INVALID_VALUE",
            message=f"value for {field_name} is outside the allowed domain",
        )
    return normalized, None
