"""Именованные domain-валидаторы межполевых инвариантов ChangeSet.

Объявленное имя без функции — атомарный REJECTED, не тихий пропуск.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError

DomainValidator = Callable[["DomainContext"], list[ControlPlaneError]]


@dataclass(frozen=True, slots=True)
class DomainContext:
    """Срез одной операции: запрошенные и слитые с поколением значения."""

    operation_index: int
    resource_id: str
    bucket: str
    requested: Mapping[str, object]
    merged: Mapping[str, object]


def _invariant(
    ctx: DomainContext,
    validator: str,
    message: str,
) -> ControlPlaneError:
    return ControlPlaneError(
        code="DOMAIN_INVARIANT",
        message=message,
        resource_id=ctx.resource_id,
        operation_index=ctx.operation_index,
        details={"validator": validator},
    )


def _as_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def non_negative_limits(ctx: DomainContext) -> list[ControlPlaneError]:
    """Числовые лимиты в операции не могут быть отрицательными. 0 допустим."""
    errors: list[ControlPlaneError] = []
    for field_name, value in ctx.requested.items():
        number = _as_number(value)
        if number is not None and number < 0:
            errors.append(
                _invariant(
                    ctx,
                    "non_negative_limits",
                    f"{field_name} must be greater than or equal to 0",
                )
            )
    return errors


def sales_target_not_above_max(ctx: DomainContext) -> list[ControlPlaneError]:
    """Если заданы обе цены, целевая не выше максимальной цены заказа."""
    target = _as_number(ctx.merged.get("target_price_for_order"))
    maximum = _as_number(ctx.merged.get("max_price_for_order"))
    if target is None or maximum is None or target <= maximum:
        return []
    return [
        _invariant(
            ctx,
            "sales_target_not_above_max",
            "target_price_for_order must not exceed max_price_for_order",
        )
    ]


def bid_control_enabled_requires_strategy(
    ctx: DomainContext,
) -> list[ControlPlaneError]:
    """Включённый bid-control требует непустую стратегию в том же поколении."""
    if ctx.merged.get("auto_shelf_bid_control_enabled") is not True:
        return []
    strategy = ctx.merged.get("auto_shelf_bid_control_strategy")
    if isinstance(strategy, str) and strategy.strip():
        return []
    return [
        _invariant(
            ctx,
            "bid_control_enabled_requires_strategy",
            "enabled bid control requires auto_shelf_bid_control_strategy",
        )
    ]


DOMAIN_VALIDATOR_IMPL: dict[str, DomainValidator] = {
    "non_negative_limits": non_negative_limits,
    "sales_target_not_above_max": sales_target_not_above_max,
    "bid_control_enabled_requires_strategy": bid_control_enabled_requires_strategy,
}


def run_declared_validators(
    names: tuple[str, ...],
    ctx: DomainContext,
) -> list[ControlPlaneError]:
    """Выполнить объявленные инварианты. Неизвестное имя — fail closed."""
    errors: list[ControlPlaneError] = []
    for name in names:
        impl = DOMAIN_VALIDATOR_IMPL.get(name)
        if impl is None:
            errors.append(
                ControlPlaneError(
                    code="DOMAIN_VALIDATOR_UNIMPLEMENTED",
                    message=f"declared invariant {name} has no implementation",
                    resource_id=ctx.resource_id,
                    operation_index=ctx.operation_index,
                    details={"validator": name},
                )
            )
            continue
        errors.extend(impl(ctx))
    return errors
