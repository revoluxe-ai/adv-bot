"""PG writer: bounded campaign settings policy mutations on AdvSetting rows."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.kernel.mutation_policy import policy_for
from app.modules.wb_sky_control_plane.models.plan import PlanV1


def _field_from_path(field_path: str) -> str:
    return field_path.rsplit(".", maxsplit=1)[-1]


def apply_plan_to_adv_settings(
    plan: PlanV1,
    *,
    adv_by_resource: dict[str, AdvSetting],
) -> None:
    """Apply validated normalized semantic changes only (no client setattr)."""
    for effect in plan.effects:
        if effect.is_no_op:
            continue
        policy = policy_for(effect.operation)
        if policy is None:
            raise ValueError(f"unsupported operation {effect.operation}")
        row = adv_by_resource.get(effect.resource_id)
        if row is None:
            raise LookupError(f"missing AdvSetting for {effect.resource_id}")
        allowed = set(policy.fields)
        for change in effect.semantic_changes:
            field_name = _field_from_path(change.field_path)
            if field_name not in allowed:
                raise ValueError(f"field {field_name} outside policy allowlist")
            setattr(row, field_name, change.normalized)
