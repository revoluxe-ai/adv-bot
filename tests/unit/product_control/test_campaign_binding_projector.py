"""Slice B: CampaignProductBindingProjector (read-only)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.product_control.application.projection.campaign_binding_projector import (
    CampaignProductBindingProjector,
)
from app.modules.product_control.application.projection.sources import (
    AdvLegProjectionSource,
    ComplexAdvProjectionSource,
)
from app.modules.product_control.domain.enums import LegRole, MembershipRole

pytestmark = pytest.mark.unit


def _complex(
    *,
    shop_id: str = "shop-a",
    auto_id: int = 100,
    auto_pg_id: int = 1,
    auto_nmids: list[int],
    search_obj: SimpleNamespace | None = None,
    search_linkage: int | None = None,
) -> ComplexAdvProjectionSource:
    auto = AdvLegProjectionSource(
        adv_setting_id=auto_pg_id,
        physical_adv_id=auto_id,
        leg_role=LegRole.AUTO,
        nmids=tuple(auto_nmids),
    )
    search_leg = None
    if search_obj is not None:
        search_leg = AdvLegProjectionSource(
            adv_setting_id=int(search_obj.id),
            physical_adv_id=int(search_obj.adv_id),
            leg_role=LegRole.SEARCH,
            nmids=tuple(search_obj.nmids),
        )
    return ComplexAdvProjectionSource(
        shop_id=shop_id,
        auto_leg=auto,
        search_leg=search_leg,
        search_linkage_adv_id=search_linkage,
    )


def test_s01_auto_and_search_separate_bindings() -> None:
    search = SimpleNamespace(id=2, adv_id=200, nmids=[42])
    source = _complex(auto_nmids=[42], search_obj=search)
    result = CampaignProductBindingProjector.project_complex(source)
    roles = {b.leg_role for b in result.bindings}
    physical = {b.physical_adv_id for b in result.bindings}
    assert roles == {LegRole.AUTO, LegRole.SEARCH}
    assert physical == {100, 200}


def test_s17_search_physical_id_not_linkage_id() -> None:
    linkage_wrong_physical = 9999
    search = SimpleNamespace(id=2, adv_id=200, nmids=[7])
    source = _complex(
        auto_nmids=[7],
        search_obj=search,
        search_linkage=linkage_wrong_physical,
    )
    result = CampaignProductBindingProjector.project_complex(source)
    search_bindings = [b for b in result.bindings if b.leg_role == LegRole.SEARCH]
    assert len(search_bindings) == 1
    assert search_bindings[0].physical_adv_id == 200
    assert search_bindings[0].physical_adv_id != linkage_wrong_physical


def test_search_linkage_without_paired_object_issue() -> None:
    source = _complex(auto_nmids=[1], search_linkage=555)
    result = CampaignProductBindingProjector.project_complex(source)
    assert any(i.code == "SEARCH_LEG_UNRESOLVED" for i in result.issues)


def test_auto_only_complex() -> None:
    source = _complex(auto_nmids=[11])
    result = CampaignProductBindingProjector.project_complex(source)
    assert len(result.bindings) == 1
    assert result.bindings[0].leg_role == LegRole.AUTO


def test_single_nmid_primary_with_evidence() -> None:
    source = _complex(auto_nmids=[55])
    binding = CampaignProductBindingProjector.project_complex(source).bindings[0]
    assert binding.membership_role == MembershipRole.PRIMARY
    assert binding.membership_evidence is not None
    assert binding.membership_evidence.source == "PG_NMIDS"


def test_duplicate_nmid_one_binding() -> None:
    source = _complex(auto_nmids=[3, 3, 3])
    result = CampaignProductBindingProjector.project_complex(source)
    assert len(result.bindings) == 1
    assert result.bindings[0].nmid == 3


def test_multi_nmid_unknown_membership() -> None:
    source = _complex(auto_nmids=[1, 2])
    result = CampaignProductBindingProjector.project_complex(source)
    assert len(result.bindings) == 2
    assert all(b.membership_role == MembershipRole.UNKNOWN for b in result.bindings)


def test_s05_main_nmid_ignored_not_primary_evidence() -> None:
    """main_nmid would be 1 (sorted) but two nmids → UNKNOWN, not PRIMARY on 1."""
    source = _complex(auto_nmids=[2, 1])
    result = CampaignProductBindingProjector.project_complex(source)
    assert all(b.membership_role == MembershipRole.UNKNOWN for b in result.bindings)


def test_deterministic_ordering() -> None:
    source = _complex(
        auto_nmids=[30, 10],
        search_obj=SimpleNamespace(id=2, adv_id=201, nmids=[20, 10]),
    )
    r1 = CampaignProductBindingProjector.project_complex(source).bindings
    r2 = CampaignProductBindingProjector.project_complex(source).bindings
    assert r1 == r2
    assert tuple(r1) == tuple(
        sorted(r1, key=lambda b: (b.leg_role.value, b.physical_adv_id, b.nmid))
    )


def test_missing_shop_id_fail_closed() -> None:
    source = _complex(shop_id="", auto_nmids=[1])
    source = ComplexAdvProjectionSource(
        shop_id=None,
        auto_leg=source.auto_leg,
        search_leg=None,
    )
    result = CampaignProductBindingProjector.project_complex(source)
    assert result.bindings == ()
    assert any(i.code == "SHOP_ID_MISSING" for i in result.issues)


def test_s02_same_nmid_two_complexes() -> None:
    nmid = 77
    r1 = CampaignProductBindingProjector.project_complex(
        _complex(auto_pg_id=1, auto_id=10, auto_nmids=[nmid])
    )
    r2 = CampaignProductBindingProjector.project_complex(
        _complex(auto_pg_id=2, auto_id=20, auto_nmids=[nmid])
    )
    assert len(r1.bindings) == 1
    assert len(r2.bindings) == 1
    assert r1.bindings[0].physical_adv_id != r2.bindings[0].physical_adv_id


def test_search_physical_id_regression_linkage_not_physical() -> None:
    """Linkage id 999 must not appear as Search physical_adv_id (paired id 200)."""
    search = SimpleNamespace(id=2, adv_id=200, nmids=[5])
    source = _complex(
        auto_nmids=[5],
        search_obj=search,
        search_linkage=999,
    )
    result = CampaignProductBindingProjector.project_complex(source)
    search_physical = [
        b.physical_adv_id for b in result.bindings if b.leg_role == LegRole.SEARCH
    ]
    assert search_physical == [200]
    assert 999 not in search_physical
