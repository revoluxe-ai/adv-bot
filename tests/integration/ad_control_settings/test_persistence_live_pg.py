"""Live PostgreSQL integration for ad control persistence (disposable test DB)."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.ad_control_settings.domain.campaign_ref import CampaignRef
from app.modules.ad_control_settings.domain.configured import DrrPolicyParamsV1
from app.modules.ad_control_settings.domain.enums import (
    AdControlFeatureId,
    AdControlFeatureMode,
    ShopFeatureActivation,
)
from app.modules.ad_control_settings.persistence.cas import (
    AdControlMutationKind,
    RevisionConflictError,
)
from app.modules.ad_control_settings.persistence.repository import (
    AdControlPersistenceError,
    AdControlSettingsRepository,
    CampaignClearUpsert,
    CampaignDisableUpsert,
    CampaignOverrideUpsert,
    ShopFeatureUpsert,
)
from app.modules.product_control.domain.drr_profile import drr_profile_from_percent

pytestmark = [pytest.mark.integration, pytest.mark.destructive_local]


def _drr() -> DrrPolicyParamsV1:
    return DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("12"), Decimal("18")),
    )


async def test_shop_round_trip_and_revision_monotonic(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    upsert = ShopFeatureUpsert(
        shop_id="int-shop-1",
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload=_drr(),
    )
    first = await repo.apply_shop_mutation(upsert, expected_revision=None)
    assert first.kind == AdControlMutationKind.CREATE
    assert first.revision == 1

    second = await repo.apply_shop_mutation(upsert, expected_revision=1)
    assert second.kind == AdControlMutationKind.NO_OP
    assert second.revision == 1

    upsert_disabled = ShopFeatureUpsert(
        shop_id="int-shop-1",
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.DISABLED,
        payload=None,
    )
    third = await repo.apply_shop_mutation(upsert_disabled, expected_revision=1)
    assert third.kind == AdControlMutationKind.DISABLE
    assert third.revision == 2
    await ad_control_session.commit()

    slots = await repo.load_shop_slots("int-shop-1")
    assert slots[AdControlFeatureId.DRR_POLICY].activation == ShopFeatureActivation.DISABLED


async def test_campaign_override_disable_clear_inherit(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-shop-2", advert_id=5001)
    override = CampaignOverrideUpsert(
        campaign=campaign,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        payload=_drr(),
    )
    created = await repo.apply_campaign_override(override, expected_revision=None)
    assert created.kind == AdControlMutationKind.CREATE
    assert created.revision == 1

    slots = await repo.load_campaign_slots(campaign)
    assert slots[AdControlFeatureId.DRR_POLICY].mode == AdControlFeatureMode.OVERRIDE

    cleared = await repo.clear_campaign_feature(
        CampaignClearUpsert(campaign=campaign, feature_id=AdControlFeatureId.DRR_POLICY),
        expected_revision=1,
    )
    assert cleared.kind == AdControlMutationKind.CLEAR_TO_INHERIT
    slots_after = await repo.load_campaign_slots(campaign)
    assert AdControlFeatureId.DRR_POLICY not in slots_after

    replay = await repo.clear_campaign_feature(
        CampaignClearUpsert(campaign=campaign, feature_id=AdControlFeatureId.DRR_POLICY),
        expected_revision=None,
    )
    assert replay.kind == AdControlMutationKind.NO_OP


async def test_unique_logical_identity_one_schema_version_slot(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    shop_id = "int-shop-3"
    await repo.apply_shop_mutation(
        ShopFeatureUpsert(
            shop_id=shop_id,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr(),
        ),
        expected_revision=None,
    )
    await ad_control_session.flush()
    await repo.apply_shop_mutation(
        ShopFeatureUpsert(
            shop_id=shop_id,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr(),
        ),
        expected_revision=1,
    )
    with pytest.raises(RevisionConflictError):
        await repo.apply_shop_mutation(
            ShopFeatureUpsert(
                shop_id=shop_id,
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=_drr(),
            ),
            expected_revision=None,
        )


async def test_aba_revision_increments_even_when_content_returns(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    async with maker() as session:
        repo = AdControlSettingsRepository(session)
        shop_id = "int-shop-aba"
        base = ShopFeatureUpsert(
            shop_id=shop_id,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr(),
        )
        r1 = await repo.apply_shop_mutation(base, expected_revision=None)
        alt = ShopFeatureUpsert(
            shop_id=shop_id,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            activation=ShopFeatureActivation.DISABLED,
            payload=None,
        )
        r2 = await repo.apply_shop_mutation(alt, expected_revision=r1.revision)
        r3 = await repo.apply_shop_mutation(base, expected_revision=r2.revision)
        assert (r1.revision, r2.revision, r3.revision) == (1, 2, 3)
        await session.commit()


async def test_stale_revision_conflict(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    shop_id = "int-shop-stale"
    created = await repo.apply_shop_mutation(
        ShopFeatureUpsert(
            shop_id=shop_id,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
            activation=ShopFeatureActivation.ENABLED,
            payload=_drr(),
        ),
        expected_revision=None,
    )
    with pytest.raises(RevisionConflictError):
        await repo.apply_shop_mutation(
            ShopFeatureUpsert(
                shop_id=shop_id,
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.DISABLED,
                payload=None,
            ),
            expected_revision=created.revision - 1,
        )


async def test_validation_failure_does_not_persist_row(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    with pytest.raises(AdControlPersistenceError):
        await repo.apply_shop_mutation(
            ShopFeatureUpsert(
                shop_id="int-shop-bad",
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=1,
                activation=ShopFeatureActivation.ENABLED,
                payload=None,
            ),
            expected_revision=None,
        )
    row = await repo.get_shop_row("int-shop-bad", AdControlFeatureId.DRR_POLICY)
    assert row is None


async def test_concurrent_create_one_wins(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def _create() -> None:
        async with maker() as session:
            repo = AdControlSettingsRepository(session)
            await repo.apply_shop_mutation(
                ShopFeatureUpsert(
                    shop_id="int-shop-race",
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    schema_version=1,
                    activation=ShopFeatureActivation.ENABLED,
                    payload=_drr(),
                ),
                expected_revision=None,
            )
            await session.commit()

    results = await asyncio.gather(_create(), _create(), return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) >= 1
    assert any(isinstance(e, IntegrityError) or isinstance(e, RevisionConflictError) for e in errors)


async def test_table_unique_constraints(async_engine: AsyncEngine) -> None:
    async with async_engine.connect() as conn:
        unique = await conn.run_sync(
            lambda sync: {
                c["name"]
                for c in inspect(sync).get_unique_constraints("adcontrolshopfeaturerow")
            }
        )
    assert "uq_ad_control_shop_feature_identity" in unique


async def test_campaign_disabled_round_trip(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-shop-dis", advert_id=77)
    result = await repo.apply_campaign_disable(
        CampaignDisableUpsert(
            campaign=campaign,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
        ),
        expected_revision=None,
    )
    assert result.kind == AdControlMutationKind.DISABLE
    slots = await repo.load_campaign_slots(campaign)
    assert slots[AdControlFeatureId.DRR_POLICY].mode == AdControlFeatureMode.DISABLED


async def test_migration_tables_exist(async_engine: AsyncEngine) -> None:
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync: inspect(sync).get_table_names()
        )
    assert "adcontrolshopfeaturerow" in tables
    assert "adcontrolcampaignfeaturerow" in tables
