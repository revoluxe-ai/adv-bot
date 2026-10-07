"""Resolve ChangeSet resource refs → authoritative CampaignResourceSnapshot."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.wb_sky_control_plane.models.changeset import ChangeSetV1
from app.modules.wb_sky_control_plane.models.enums import CampaignLegRole, MappingStatus
from app.modules.wb_sky_control_plane.models.errors import ControlPlaneError
from app.modules.wb_sky_control_plane.models.snapshot import (
    CampaignResourceSnapshotV1,
    LocalPolicyStateV1,
)
from app.modules.wb_sky_control_plane.ports.wb_read_port import WbPromotionV2ReadPort
from app.modules.wb_sky_control_plane.read.local_policy import (
    project_local_policy_from_adv_setting,
)
from app.modules.wb_sky_control_plane.read.normalizer import normalize_wb_campaign_leg
from app.modules.wb_sky_control_plane.read.scope import resolve_wb_cabinet_id
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry
from app.modules.wb_sky_control_plane.kernel.classify import classify_snapshot
from app.modules.wb_sky_control_plane.kernel.state_token import compute_state_token


def _ops_by_resource(changeset: ChangeSetV1) -> dict[str, frozenset[str]]:
    grouped: dict[str, set[str]] = defaultdict(set)
    for operation in changeset.operations:
        grouped[operation.resource.resource_id].add(operation.op)
    return {rid: frozenset(ops) for rid, ops in grouped.items()}


async def resolve_changeset_snapshots(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    wb_reader: WbPromotionV2ReadPort,
) -> tuple[dict[str, CampaignResourceSnapshotV1], list[ControlPlaneError]]:
    """Verify shop scope, batch WB reads, normalize legs, report broken mappings."""
    errors: list[ControlPlaneError] = []
    wb_cabinet_id = await resolve_wb_cabinet_id(session, changeset.scope)
    if wb_cabinet_id is None:
        errors.append(
            ControlPlaneError(
                code="SHOP_SCOPE_NOT_FOUND",
                message="shop_id not found for provider scope",
                details={
                    "provider": changeset.scope.provider,
                    "shop_id": changeset.scope.shop_id,
                },
            )
        )
        return {}, errors

    resource_ids = {op.resource.resource_id for op in changeset.operations}
    ops_by_resource = _ops_by_resource(changeset)

    registry_rows = await session.execute(
        select(WbSkyCampaignResourceRegistry).where(
            WbSkyCampaignResourceRegistry.resource_id.in_(resource_ids)
        )
    )
    registry_by_id = {
        row.resource_id: row for row in registry_rows.scalars().all()
    }

    adv_ids_to_fetch: set[int] = set()
    for reg in registry_by_id.values():
        if reg.wb_cabinet_id != wb_cabinet_id:
            errors.append(
                ControlPlaneError(
                    code="SHOP_SCOPE_MISMATCH",
                    message="Registry row cabinet does not match ChangeSet scope",
                    resource_id=reg.resource_id,
                    details={
                        "expected_shop_id": changeset.scope.shop_id,
                        "actual_wb_cabinet_id": str(reg.wb_cabinet_id),
                    },
                )
            )
            continue
        if reg.auto_adv_id is not None:
            adv_ids_to_fetch.add(reg.auto_adv_id)
        if reg.search_adv_id is not None:
            adv_ids_to_fetch.add(reg.search_adv_id)

    raw_by_id: dict[int, Mapping[str, object]] = {}
    scope_errors = {e.code for e in errors}
    if adv_ids_to_fetch and "SHOP_SCOPE_MISMATCH" not in scope_errors:
        try:
            raw_items = await wb_reader.fetch_adverts_raw_by_ids(sorted(adv_ids_to_fetch))
        except ValueError as exc:
            errors.append(
                ControlPlaneError(
                    code="WB_READ_MALFORMED",
                    message=str(exc),
                )
            )
            raw_items = []
        for raw in raw_items:
            wb_id_raw = raw.get("id")
            if isinstance(wb_id_raw, int):
                raw_by_id[wb_id_raw] = raw
            elif isinstance(wb_id_raw, str) and wb_id_raw.isdigit():
                raw_by_id[int(wb_id_raw)] = raw

    snapshots: dict[str, CampaignResourceSnapshotV1] = {}
    for resource_id in resource_ids:
        reg = registry_by_id.get(resource_id)
        if reg is None:
            errors.append(
                ControlPlaneError(
                    code="RESOURCE_NOT_REGISTERED",
                    message="cmp_* resource_id not found in registry",
                    resource_id=resource_id,
                )
            )
            continue
        if reg.wb_cabinet_id != wb_cabinet_id:
            continue

        auto_leg = None
        search_leg = None
        mapping_status = MappingStatus.OK
        if reg.auto_adv_id is not None:
            raw_auto = raw_by_id.get(reg.auto_adv_id)
            if raw_auto is None:
                mapping_status = MappingStatus.BROKEN
            else:
                auto_leg = normalize_wb_campaign_leg(raw_auto, role=CampaignLegRole.AUTO)
        if reg.search_adv_id is not None:
            raw_search = raw_by_id.get(reg.search_adv_id)
            if raw_search is None:
                mapping_status = MappingStatus.BROKEN
            else:
                search_leg = normalize_wb_campaign_leg(
                    raw_search, role=CampaignLegRole.SEARCH
                )

        local_policy = LocalPolicyStateV1()
        adv_setting_id = reg.adv_setting_id
        if reg.adv_setting_id is not None:
            adv_row = await session.get(AdvSetting, reg.adv_setting_id)
            if adv_row is not None:
                local_policy = project_local_policy_from_adv_setting(adv_row)

        product_nm_ids: list[int] = []
        if auto_leg is not None:
            product_nm_ids.extend(auto_leg.nm_ids)
        if search_leg is not None:
            product_nm_ids.extend(search_leg.nm_ids)
        product_nm_ids = sorted(set(product_nm_ids))

        snapshot = CampaignResourceSnapshotV1(
            resource_id=resource_id,
            wb_cabinet_id=reg.wb_cabinet_id,
            adv_setting_id=adv_setting_id,
            auto_leg=auto_leg,
            search_leg=search_leg,
            product_nm_ids=product_nm_ids,
            local_policy=local_policy,
            mapping_status=mapping_status,
        )
        snapshot.classification = classify_snapshot(snapshot)
        target_ops = ops_by_resource.get(resource_id, frozenset())
        snapshot.state_token = compute_state_token(snapshot, target_op_kinds=target_ops)
        snapshots[resource_id] = snapshot

        if mapping_status == MappingStatus.BROKEN:
            errors.append(
                ControlPlaneError(
                    code="BROKEN_WB_MAPPING",
                    message="Authoritative WB read missing for registry anchor",
                    resource_id=resource_id,
                )
            )
    return snapshots, errors
