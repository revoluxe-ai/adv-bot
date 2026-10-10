"""Live PostgreSQL integration for ad control persistence (disposable test DB)."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, PendingRollbackError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.ad_control_settings.persistence.cas import UnsupportedSchemaVersionError
from app.modules.ad_control_settings.persistence.revision_ledger import (
    SlotMutationKey,
    read_mutation_revision,
)

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
from app.modules.ad_control_settings.persistence.payload_codec import encode_payload_json
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
    assert len(errors) == 1
    assert isinstance(errors[0], RevisionConflictError)


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


async def test_campaign_disable_no_op_preserves_revision(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-shop-dis-noop", advert_id=88)
    disable = CampaignDisableUpsert(
        campaign=campaign,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
    )
    first = await repo.apply_campaign_disable(disable, expected_revision=None)
    row = await repo.get_campaign_row(campaign, AdControlFeatureId.DRR_POLICY)
    assert row is not None
    token_before = row.state_token
    updated_before = row.updated_at
    second = await repo.apply_campaign_disable(disable, expected_revision=first.revision)
    assert second.kind == AdControlMutationKind.NO_OP
    row_after = await repo.get_campaign_row(campaign, AdControlFeatureId.DRR_POLICY)
    assert row_after is not None
    assert row_after.revision == first.revision
    assert row_after.state_token == token_before
    assert row_after.updated_at == updated_before


async def test_campaign_override_no_op_preserves_revision(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-shop-ov-noop", advert_id=89)
    override = CampaignOverrideUpsert(
        campaign=campaign,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        payload=_drr(),
    )
    first = await repo.apply_campaign_override(override, expected_revision=None)
    row = await repo.get_campaign_row(campaign, AdControlFeatureId.DRR_POLICY)
    assert row is not None
    token_before = row.state_token
    second = await repo.apply_campaign_override(override, expected_revision=first.revision)
    assert second.kind == AdControlMutationKind.NO_OP
    row_after = await repo.get_campaign_row(campaign, AdControlFeatureId.DRR_POLICY)
    assert row_after is not None
    assert row_after.revision == first.revision
    assert row_after.state_token == token_before


async def test_clear_recreate_aba_new_revision_and_token(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-shop-aba-camp", advert_id=900)
    override = CampaignOverrideUpsert(
        campaign=campaign,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        payload=_drr(),
    )
    first = await repo.apply_campaign_override(override, expected_revision=None)
    first_token = first.state_token
    await repo.clear_campaign_feature(
        CampaignClearUpsert(campaign=campaign, feature_id=AdControlFeatureId.DRR_POLICY),
        expected_revision=first.revision,
    )
    with pytest.raises(RevisionConflictError):
        await repo.apply_campaign_override(override, expected_revision=first.revision)
    second = await repo.apply_campaign_override(override, expected_revision=None)
    assert second.revision != first.revision
    assert second.state_token != first_token


async def test_concurrent_campaign_create_one_wins(async_engine: AsyncEngine) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)
    campaign = CampaignRef(shop_id="int-camp-race", advert_id=5010)

    async def _create() -> None:
        async with maker() as session:
            repo = AdControlSettingsRepository(session)
            await repo.apply_campaign_override(
                CampaignOverrideUpsert(
                    campaign=campaign,
                    feature_id=AdControlFeatureId.DRR_POLICY,
                    schema_version=1,
                    payload=_drr(),
                ),
                expected_revision=None,
            )
            await session.commit()

    results = await asyncio.gather(_create(), _create(), return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    assert len(errors) == 1
    assert isinstance(errors[0], RevisionConflictError)


async def test_stale_clear_revision(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-stale-clear", advert_id=77)
    created = await repo.apply_campaign_disable(
        CampaignDisableUpsert(
            campaign=campaign,
            feature_id=AdControlFeatureId.DRR_POLICY,
            schema_version=1,
        ),
        expected_revision=None,
    )
    with pytest.raises(RevisionConflictError):
        await repo.clear_campaign_feature(
            CampaignClearUpsert(campaign=campaign, feature_id=AdControlFeatureId.DRR_POLICY),
            expected_revision=created.revision + 99,
        )


async def test_unsupported_schema_fail_closed(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    with pytest.raises(UnsupportedSchemaVersionError):
        await repo.apply_shop_mutation(
            ShopFeatureUpsert(
                shop_id="int-bad-schema",
                feature_id=AdControlFeatureId.DRR_POLICY,
                schema_version=99,
                activation=ShopFeatureActivation.DISABLED,
                payload=None,
            ),
            expected_revision=None,
        )


async def test_no_op_does_not_consume_ledger_revision(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    campaign = CampaignRef(shop_id="int-ledger-noop", advert_id=901)
    disable = CampaignDisableUpsert(
        campaign=campaign,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
    )
    first = await repo.apply_campaign_disable(disable, expected_revision=None)
    key = SlotMutationKey.for_campaign(campaign, AdControlFeatureId.DRR_POLICY)
    ledger_after_create = await read_mutation_revision(ad_control_session, key)
    assert ledger_after_create == first.revision
    second = await repo.apply_campaign_disable(disable, expected_revision=first.revision)
    assert second.kind == AdControlMutationKind.NO_OP
    ledger_after_noop = await read_mutation_revision(ad_control_session, key)
    assert ledger_after_noop == ledger_after_create


async def test_migration_tables_exist(async_engine: AsyncEngine) -> None:
    async with async_engine.connect() as conn:
        tables = await conn.run_sync(
            lambda sync: inspect(sync).get_table_names()
        )
    assert "adcontrolshopfeaturerow" in tables
    assert "adcontrolcampaignfeaturerow" in tables
    assert "adcontrolslotmutationledger" in tables


async def test_shop_enabled_payload_update(ad_control_session) -> None:
    repo = AdControlSettingsRepository(ad_control_session)
    shop_id = "int-shop-update"
    base = ShopFeatureUpsert(
        shop_id=shop_id,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload=_drr(),
    )
    created = await repo.apply_shop_mutation(base, expected_revision=None)
    assert created.kind == AdControlMutationKind.CREATE
    alt_profile = DrrPolicyParamsV1(
        profile=drr_profile_from_percent(Decimal("20"), Decimal("25")),
    )
    updated_upsert = ShopFeatureUpsert(
        shop_id=shop_id,
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload=alt_profile,
    )
    updated = await repo.apply_shop_mutation(
        updated_upsert, expected_revision=created.revision
    )
    assert updated.kind == AdControlMutationKind.UPDATE
    assert updated.revision == created.revision + 1
    row = await repo.get_shop_row(shop_id, AdControlFeatureId.DRR_POLICY)
    assert row is not None
    assert row.revision == updated.revision


async def test_concurrent_create_does_not_leak_integrity_error(
    async_engine: AsyncEngine,
) -> None:
    maker = async_sessionmaker(async_engine, expire_on_commit=False)

    async def _create() -> None:
        async with maker() as session:
            repo = AdControlSettingsRepository(session)
            await repo.apply_shop_mutation(
                ShopFeatureUpsert(
                    shop_id="int-shop-leak",
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
    assert len(errors) == 1
    assert isinstance(errors[0], RevisionConflictError)
    assert not any(isinstance(r, IntegrityError) for r in errors)


async def test_flush_conflict_requires_rollback_before_reuse(
    ad_control_session,
) -> None:
    from datetime import UTC, datetime

    from app.modules.ad_control_settings.persistence.models import (
        AdControlShopFeatureRow,
    )
    from app.modules.ad_control_settings.persistence.repository import (
        _flush_or_conflict,
    )

    repo = AdControlSettingsRepository(ad_control_session)
    upsert = ShopFeatureUpsert(
        shop_id="int-shop-rollback",
        feature_id=AdControlFeatureId.DRR_POLICY,
        schema_version=1,
        activation=ShopFeatureActivation.ENABLED,
        payload=_drr(),
    )
    created = await repo.apply_shop_mutation(upsert, expected_revision=None)
    assert created.revision == 1
    payload_json = encode_payload_json(upsert.feature_id, upsert.payload)
    duplicate = AdControlShopFeatureRow(
        shop_id=upsert.shop_id,
        feature_id=upsert.feature_id.value,
        schema_version=upsert.schema_version,
        activation=upsert.activation.value,
        payload_json=payload_json,
        revision=99,
        state_token="duplicate-token",
        updated_at=datetime.now(tz=UTC),
    )
    ad_control_session.add(duplicate)
    with pytest.raises(RevisionConflictError):
        await _flush_or_conflict(ad_control_session, scope="shop duplicate")
    with pytest.raises(PendingRollbackError):
        await repo.get_shop_row(upsert.shop_id, upsert.feature_id)
    await ad_control_session.rollback()
    row = await repo.get_shop_row(upsert.shop_id, upsert.feature_id)
    assert row is None
    second = await repo.apply_shop_mutation(upsert, expected_revision=None)
    assert second.kind == AdControlMutationKind.CREATE
