"""PG writer: bounded campaign settings policy mutations on AdvSetting rows."""

from __future__ import annotations

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.kernel.mutation_policy import policy_for
from app.modules.wb_sky_control_plane.models.plan import PlanV1


def _field_name_from_path(field_path: str) -> str:
    return field_path.rsplit(".", maxsplit=1)[-1]


def _bucket_from_path(field_path: str, resource_id: str) -> str | None:
    prefix = f"{resource_id}."
    if not field_path.startswith(prefix):
        return None
    remainder = field_path[len(prefix) :]
    parts = remainder.split(".", maxsplit=1)
    if len(parts) != 2:
        return None
    return parts[0]


def apply_plan_to_adv_settings(
    plan: PlanV1,
    *,
    adv_by_resource: dict[str, AdvSetting],
) -> None:
    """Apply validated normalized semantic changes only (no client setattr)."""
    for effect in plan.effects:
        if effect.is_no_op:
            raise ValueError("NO_OP effect must not enter mutation apply path")
        policy = policy_for(effect.operation)
        if policy is None:
            raise ValueError(f"unsupported operation {effect.operation}")
        row = adv_by_resource.get(effect.resource_id)
        if row is None:
            raise LookupError(f"missing AdvSetting for {effect.resource_id}")
        allowed = set(policy.fields)
        for change in effect.semantic_changes:
            if change.resource_id is not None and change.resource_id != effect.resource_id:
                raise ValueError("change resource_id disagrees with effect")
            bucket = _bucket_from_path(change.field_path, effect.resource_id)
            if bucket != policy.bucket:
                raise ValueError("field_path bucket disagrees with operation policy")
            field_name = _field_name_from_path(change.field_path)
            if field_name not in allowed:
                raise ValueError(f"field {field_name} outside policy allowlist")
            setattr(row, field_name, change.normalized)
