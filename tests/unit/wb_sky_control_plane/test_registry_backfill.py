"""Registry backfill idempotency and shadow/ambiguous skip tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.wb_sky_control_plane.registry.anchor import (
    build_anchor_fingerprint,
    generate_resource_id,
)
from app.modules.wb_sky_control_plane.registry.backfill import (
    backfill_campaign_resource_registry,
)

pytestmark = pytest.mark.unit


def test_anchor_fingerprint_is_stable() -> None:
    """Anchor fingerprint ordering is deterministic."""
    fp = build_anchor_fingerprint(
        wb_cabinet_id=1,
        auto_adv_id=100,
        search_adv_id=200,
        nm_ids=[3, 1, 2],
    )
    assert "nm=1,2,3" in fp


def test_resource_id_is_uuid_opaque_not_wb_derived() -> None:
    """resource_id must be random cmp_* independent of anchor fingerprint."""
    rid_a = generate_resource_id()
    rid_b = generate_resource_id()
    assert rid_a.startswith("cmp_")
    assert rid_b.startswith("cmp_")
    assert rid_a != rid_b
    fp = build_anchor_fingerprint(
        wb_cabinet_id=1,
        auto_adv_id=100,
        search_adv_id=200,
        nm_ids=[1],
    )
    assert fp not in rid_a


@pytest.mark.asyncio
async def test_backfill_skips_search_shadow_by_topology() -> None:
    """Shadow row: adv_id equals another row's physical _search_adv_id."""
    primary = SimpleNamespace(
        adv_id=100,
        _search_adv_id=555,
        wb_cabinet_id=1,
        nmids=[1],
        id=11,
    )
    shadow = SimpleNamespace(
        adv_id=555,
        _search_adv_id=None,
        wb_cabinet_id=1,
        nmids=[1],
        id=10,
    )
    unique = SimpleNamespace(
        adv_id=300,
        _search_adv_id=None,
        wb_cabinet_id=1,
        nmids=[9],
        id=13,
    )

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [shadow, primary, unique]

    empty_scalar = MagicMock()
    empty_scalar.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(
        side_effect=[execute_result] + [empty_scalar] * 10
    )

    stats = await backfill_campaign_resource_registry(session, dry_run=True)
    assert stats.skipped_shadow == 1
    assert stats.inserted == 2


@pytest.mark.asyncio
async def test_backfill_skips_shared_search_and_self_reference() -> None:
    """Shared _search_adv_id and self-reference are ambiguous."""
    self_ref = SimpleNamespace(
        adv_id=200,
        _search_adv_id=200,
        wb_cabinet_id=1,
        nmids=[1],
        id=20,
    )
    shared_a = SimpleNamespace(
        adv_id=100,
        _search_adv_id=500,
        wb_cabinet_id=1,
        nmids=[1],
        id=21,
    )
    shared_b = SimpleNamespace(
        adv_id=101,
        _search_adv_id=500,
        wb_cabinet_id=1,
        nmids=[2],
        id=22,
    )

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [
        self_ref,
        shared_a,
        shared_b,
    ]
    session.execute = AsyncMock(return_value=execute_result)

    stats = await backfill_campaign_resource_registry(session, dry_run=True)
    assert stats.skipped_ambiguous == 3
    assert stats.inserted == 0


@pytest.mark.asyncio
async def test_backfill_rerun_reuses_existing_by_adv_setting_id() -> None:
    """Idempotent rerun must not regenerate resource_id for same adv_setting_id."""
    row = SimpleNamespace(
        adv_id=100,
        _search_adv_id=200,
        wb_cabinet_id=1,
        nmids=[1],
        id=11,
    )
    existing_registry = SimpleNamespace(
        resource_id="cmp_existing001",
        adv_setting_id=11,
    )

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [row]

    existing_scalar = MagicMock()
    existing_scalar.scalar_one_or_none.return_value = existing_registry
    session.execute = AsyncMock(side_effect=[execute_result, existing_scalar])

    stats = await backfill_campaign_resource_registry(session, dry_run=True)
    assert stats.skipped_existing == 1
    assert stats.inserted == 0


@pytest.mark.asyncio
async def test_backfill_ignores_name_derived_search_adv_id() -> None:
    """Must use physical _search_adv_id only; property inference is ignored."""
    row_with_name_only = SimpleNamespace(
        adv_id=400,
        _search_adv_id=None,
        wb_cabinet_id=1,
        nmids=[5],
        id=40,
    )

    session = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = [row_with_name_only]

    empty_scalar = MagicMock()
    empty_scalar.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(side_effect=[execute_result, empty_scalar, empty_scalar])

    stats = await backfill_campaign_resource_registry(session, dry_run=True)
    assert stats.inserted == 1
    assert stats.skipped_shadow == 0
