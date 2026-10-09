"""Shared harness for ApplyAuthorityService disposable-PG tests."""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.modules.common_slaves.wildberries.models.models import AdvSetting
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.modules.wb_sky_control_plane.apply.constants import APPLY_CONTRACT_VERSION
from app.modules.wb_sky_control_plane.apply.enums import TransportChannel
from app.modules.wb_sky_control_plane.apply.models.context import (
    ApplyInvocationContext,
    PermissionGrantsV1,
    PrincipalRefV1,
    ShopAuthorizationV1,
)
from app.modules.wb_sky_control_plane.apply.models.receipt import DryRunReceiptBindingV1
from app.modules.wb_sky_control_plane.apply.persistence.postgres_stores import (
    PostgresDryRunReceiptStore,
)
from app.modules.wb_sky_control_plane.apply.service.apply_authority_service import (
    ApplyAuthorityService,
)
from app.modules.wb_sky_control_plane.apply.service.revalidation import (
    project_apply_binding_material,
)
from app.modules.wb_sky_control_plane.apply.service.test_hooks import ApplyServiceTestHooks
from app.modules.wb_sky_control_plane.models.changeset import (
    CampaignOperationV1,
    ChangeSetV1,
    OperationPreconditionV1,
)
from app.modules.wb_sky_control_plane.models.enums import DryRunStatus
from app.modules.wb_sky_control_plane.read.resolver import resolve_changeset_snapshots
from app.modules.wb_sky_control_plane.registry.model import WbSkyCampaignResourceRegistry


class FakeWbReader:
    """Minimal WB promotion reader for registry resolve."""

    def __init__(self, *, fail_fetch: bool = False) -> None:
        self.fail_fetch = fail_fetch
        self.fetch_count = 0

    async def fetch_adverts_raw_by_ids(
        self, adv_ids: list[int]
    ) -> list[Mapping[str, object]]:
        self.fetch_count += 1
        if self.fail_fetch:
            raise RuntimeError("wb read forced failure")
        out: list[Mapping[str, object]] = []
        for adv_id in adv_ids:
            out.append(
                {
                    "id": adv_id,
                    "bid_type": "unified" if adv_id % 2 == 0 else "manual",
                    "status": 9,
                    "settings": {
                        "payment_type": "cpm",
                        "placements": {"search": False, "recommendations": True},
                        "name": f"c-{adv_id}",
                    },
                    "nm_settings": [{"nm_id": 777}],
                }
            )
        return out


def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def make_service(
    engine: AsyncEngine,
    reader: FakeWbReader,
    *,
    hooks: ApplyServiceTestHooks | None = None,
) -> ApplyAuthorityService:
    return ApplyAuthorityService(
        session_factory=session_factory(engine),
        wb_reader=reader,
        test_hooks=hooks,
    )


def auth_context(shop_id: str, *, authorized: bool = True) -> ApplyInvocationContext:
    return ApplyInvocationContext(
        principal_ref=PrincipalRefV1(kind="wb_user", principal_id="u_test"),
        shop_authorization=ShopAuthorizationV1(
            shop_id=shop_id, authorized=authorized
        ),
        permission_grants=PermissionGrantsV1(apply_campaign_settings=True),
        transport_channel=TransportChannel.INTERNAL,
        auth_proof_ref="sess_test",
    )


async def bind_state_token(
    changeset: ChangeSetV1,
    *,
    session: AsyncSession,
    reader: FakeWbReader,
) -> ChangeSetV1:
    snapshots, errors = await resolve_changeset_snapshots(
        changeset,
        session=session,
        wb_reader=reader,
    )
    assert errors == []
    operations: list[CampaignOperationV1] = []
    for operation in changeset.operations:
        token = snapshots[operation.resource.resource_id].state_token
        assert token
        operations.append(
            operation.model_copy(
                update={"preconditions": OperationPreconditionV1(state_token=token)}
            )
        )
    return changeset.model_copy(update={"operations": operations})


async def seed_campaign(
    session: AsyncSession,
    *,
    auto_budget_daily_limit: int = 50,
) -> tuple[str, str, int]:
    """Returns shop_id, resource_id, adv_setting.id."""
    shop_id = f"shop_{uuid.uuid4().hex[:10]}"
    resource_id = f"cmp_{uuid.uuid4().hex[:12]}"
    cab = WBCabinet(
        shop_id=shop_id,
        active=True,
        demo=True,
        balance=0.0,
        bonus=0.0,
    )
    session.add(cab)
    await session.flush()
    adv = AdvSetting(
        name="apply-test",
        wb_cabinet_id=cab.id,
        adv_id=100_000 + (cab.id or 0),
        active_status="done",
        auto_budget_watchdog_enabled=False,
        auto_budget_daily_limit=auto_budget_daily_limit,
    )
    session.add(adv)
    await session.flush()
    reg = WbSkyCampaignResourceRegistry(
        resource_id=resource_id,
        wb_cabinet_id=cab.id,
        adv_setting_id=adv.id,
        auto_adv_id=100,
        search_adv_id=200,
        anchor_fingerprint=f"fp_{uuid.uuid4().hex}",
    )
    session.add(reg)
    await session.flush()
    assert adv.id is not None
    return shop_id, resource_id, adv.id


async def seed_campaign_committed(engine: AsyncEngine, **kwargs: int) -> tuple[str, str, int]:
    maker = session_factory(engine)
    async with maker() as session:
        async with session.begin():
            return await seed_campaign(session, **kwargs)


async def load_adv(engine: AsyncEngine, adv_id: int) -> AdvSetting:
    maker = session_factory(engine)
    async with maker() as session:
        row = await session.get(AdvSetting, adv_id)
        assert row is not None
        return row


async def issue_receipt(
    session: AsyncSession,
    *,
    changeset: ChangeSetV1,
    reader: FakeWbReader,
    receipt_id: str,
    capability_projection_digest: str | None = None,
    state_tokens: dict[str, str] | None = None,
) -> DryRunReceiptBindingV1:
    material = await project_apply_binding_material(
        changeset,
        session=session,
        wb_reader=reader,
    )
    assert material.status == DryRunStatus.OK
    now = datetime.now(timezone.utc)
    binding = DryRunReceiptBindingV1(
        receipt_id=receipt_id,
        issued_at=now,
        expires_at=now + timedelta(hours=2),
        scope=changeset.scope,
        changeset_id=changeset.changeset_id,
        semantic_digest=material.semantic_digest,
        preview_digest=material.preview_digest,
        state_tokens=state_tokens or material.state_tokens,
        capability_projection_digest=capability_projection_digest
        or material.capability_projection_digest,
        dry_run_status=DryRunStatus.OK,
    )
    await PostgresDryRunReceiptStore(session).insert_issued(binding)
    return binding


async def issue_receipt_committed(
    engine: AsyncEngine,
    *,
    changeset: ChangeSetV1,
    reader: FakeWbReader,
    receipt_id: str,
    **kwargs: object,
) -> DryRunReceiptBindingV1:
    maker = session_factory(engine)
    async with maker() as session:
        async with session.begin():
            return await issue_receipt(
                session,
                changeset=changeset,
                reader=reader,
                receipt_id=receipt_id,
                **kwargs,  # type: ignore[arg-type]
            )


async def prepare_bound_changeset(
    engine: AsyncEngine,
    reader: FakeWbReader,
    changeset: ChangeSetV1,
) -> ChangeSetV1:
    maker = session_factory(engine)
    async with maker() as session:
        async with session.begin():
            return await bind_state_token(changeset, session=session, reader=reader)
