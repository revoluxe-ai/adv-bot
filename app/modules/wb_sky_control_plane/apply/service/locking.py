"""Row locks for Apply Authority single-transaction mutations."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import noload

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.read.scope import resolve_wb_cabinet_id
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry


async def lock_touched_adv_settings(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
) -> tuple[dict[str, AdvSetting], dict[str, WbSkyCampaignResourceRegistry]]:
    """``SELECT … FOR UPDATE`` on AdvSetting rows in deterministic order."""
    wb_cabinet_id = await resolve_wb_cabinet_id(session, changeset.scope)
    if wb_cabinet_id is None:
        return {}, {}

    resource_ids = sorted({op.resource.resource_id for op in changeset.operations})
    registry_result = await session.execute(
        select(WbSkyCampaignResourceRegistry).where(
            WbSkyCampaignResourceRegistry.resource_id.in_(resource_ids)
        )
    )
    registry_by_id = {
        row.resource_id: row for row in registry_result.scalars().all()
    }

    adv_ids: list[int] = []
    for resource_id in resource_ids:
        reg = registry_by_id.get(resource_id)
        if reg is None or reg.adv_setting_id is None:
            continue
        if reg.wb_cabinet_id != wb_cabinet_id:
            continue
        adv_ids.append(reg.adv_setting_id)

    adv_by_id: dict[int, AdvSetting] = {}
    for adv_id in sorted(set(adv_ids)):
        result = await session.execute(
            select(AdvSetting)
            .options(noload(AdvSetting.wb_cabinet))
            .where(AdvSetting.id == adv_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is not None:
            adv_by_id[adv_id] = row

    adv_by_resource: dict[str, AdvSetting] = {}
    for resource_id in resource_ids:
        reg = registry_by_id.get(resource_id)
        if reg is None or reg.adv_setting_id is None:
            continue
        locked = adv_by_id.get(reg.adv_setting_id)
        if locked is not None:
            adv_by_resource[resource_id] = locked

    return adv_by_resource, registry_by_id
