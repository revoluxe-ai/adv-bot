"""Unit: multi-nm fail-closed, main_nmid, bindings PRIMARY evidence."""

from __future__ import annotations

import pytest

from app.modules.product_control.domain.bindings import (
    CampaignProductBinding,
    MembershipEvidence,
)
from app.modules.product_control.domain.enums import (
    LegRole,
    MembershipRole,
    ProductControlBlockerReason,
)
from app.modules.product_control.domain.models import ProductRef
from app.modules.product_control.domain.multi_nm_policy import (
    ControlProductAmbiguous,
    ControlProductResolved,
    main_nmid_is_not_control_authority,
    resolve_control_product_for_complex,
)

pytestmark = pytest.mark.unit


def test_single_nmid_resolves_control_product() -> None:
    result = resolve_control_product_for_complex("shop", [42])
    assert isinstance(result, ControlProductResolved)
    assert result.product == ProductRef("shop", 42)


def test_multi_nmid_without_authority_ambiguous() -> None:
    result = resolve_control_product_for_complex("shop", [1, 2])
    assert isinstance(result, ControlProductAmbiguous)
    assert result.reason == ProductControlBlockerReason.PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS


def test_main_nmid_not_authority_when_multiple() -> None:
    nmids = [200, 100]
    main = sorted(nmids)[0]
    assert main_nmid_is_not_control_authority(main, nmids) is True
    ambiguous = resolve_control_product_for_complex("s", nmids)
    assert ambiguous.reason == ProductControlBlockerReason.PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS


def test_primary_binding_requires_evidence() -> None:
    with pytest.raises(ValueError, match="PRIMARY"):
        CampaignProductBinding(
            shop_id="s",
            nmid=1,
            physical_adv_id=10,
            adv_setting_id=5,
            leg_role=LegRole.AUTO,
            membership_role=MembershipRole.PRIMARY,
            membership_evidence=None,
        )


def test_auto_search_leg_roles_distinct() -> None:
    evidence = MembershipEvidence(source="single_member_complex")
    auto = CampaignProductBinding(
        shop_id="s",
        nmid=1,
        physical_adv_id=10,
        adv_setting_id=5,
        leg_role=LegRole.AUTO,
        membership_role=MembershipRole.PRIMARY,
        membership_evidence=evidence,
    )
    search = CampaignProductBinding(
        shop_id="s",
        nmid=1,
        physical_adv_id=11,
        adv_setting_id=5,
        leg_role=LegRole.SEARCH,
        membership_role=MembershipRole.UNKNOWN,
        membership_evidence=None,
    )
    assert auto.leg_role != search.leg_role
    assert auto.physical_adv_id != search.physical_adv_id
