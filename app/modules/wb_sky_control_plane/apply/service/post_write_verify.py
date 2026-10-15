"""Transaction-local post-write verification via PostgreSQL reread."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.kernel.mutation_policy import (
    normalize_registered_value,
    policy_for,
)
from app.modules.wb_sky_control_plane.models.plan import PlanV1


def _scalar_db_value(raw: object) -> object:
    value = getattr(raw, "value", raw)
    return value


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


async def reread_adv_settings_by_id(
    session: AsyncSession,
    adv_setting_ids: list[int],
) -> dict[int, AdvSetting]:
    """Reread touched rows from PostgreSQL (populate-existing semantics)."""
    if not adv_setting_ids:
        return {}
    result = await session.execute(
        select(AdvSetting)
        .options(noload(AdvSetting.wb_cabinet))
        .where(AdvSetting.id.in_(sorted(set(adv_setting_ids))))
        .execution_options(populate_existing=True)
    )
    return {row.id: row for row in result.scalars().all()}


async def verify_plan_against_db_reread(
    session: AsyncSession,
    plan: PlanV1,
    *,
    adv_by_resource: dict[str, AdvSetting],
) -> bool:
    """Compare intended normalized mutations to canonical DB state after flush."""
    resource_to_adv_id = {rid: row.id for rid, row in adv_by_resource.items()}
    fresh_by_id = await reread_adv_settings_by_id(
        session, list(resource_to_adv_id.values())
    )

    for effect in plan.effects:
        if effect.is_no_op:
            continue
        policy = policy_for(effect.operation)
        if policy is None:
            return False
        adv_id = resource_to_adv_id.get(effect.resource_id)
        if adv_id is None:
            return False
        row = fresh_by_id.get(adv_id)
        if row is None:
            return False
        for change in effect.semantic_changes:
            if change.resource_id is not None and change.resource_id != effect.resource_id:
                return False
            bucket = _bucket_from_path(change.field_path, effect.resource_id)
            if bucket != policy.bucket:
                return False
            field_name = _field_name_from_path(change.field_path)
            if field_name not in policy.fields:
                return False
            db_scalar = _scalar_db_value(getattr(row, field_name, None))
            normalized_db, norm_err = normalize_registered_value(field_name, db_scalar)
            if norm_err is not None:
                return False
            if normalized_db != change.normalized:
                return False
    return True
