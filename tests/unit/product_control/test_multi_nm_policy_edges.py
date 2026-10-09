"""Edge matrix: control product resolution (fail-closed, deterministic)."""

from __future__ import annotations

import pytest

from app.modules.product_control.domain.enums import ProductControlBlockerReason
from app.modules.product_control.domain.models import ProductRef
from app.modules.product_control.domain.multi_nm_policy import (
    ControlProductAmbiguous,
    ControlProductResolved,
    main_nmid_is_not_control_authority,
    resolve_control_product_for_complex,
)

pytestmark = pytest.mark.unit


def test_empty_membership_ambiguous() -> None:
    result = resolve_control_product_for_complex("shop", [])
    assert isinstance(result, ControlProductAmbiguous)


def test_single_nmid_resolves() -> None:
    result = resolve_control_product_for_complex("shop", [99])
    assert result.product == ProductRef("shop", 99)


def test_duplicate_nmids_single_product() -> None:
    result = resolve_control_product_for_complex("shop", [5, 5, 5])
    assert result.product == ProductRef("shop", 5)


def test_multi_without_authority_ambiguous() -> None:
    result = resolve_control_product_for_complex("shop", [2, 1])
    assert isinstance(result, ControlProductAmbiguous)


def test_ordering_does_not_change_resolution() -> None:
    a = resolve_control_product_for_complex("shop", [3, 1, 2])
    b = resolve_control_product_for_complex("shop", [1, 2, 3])
    assert isinstance(a, ControlProductAmbiguous)
    assert isinstance(b, ControlProductAmbiguous)


def test_authoritative_member_in_multi_resolves() -> None:
    result = resolve_control_product_for_complex(
        "shop",
        [10, 20],
        authoritative_control_nmid=20,
    )
    assert result.product == ProductRef("shop", 20)


def test_authoritative_not_in_membership_ambiguous() -> None:
    result = resolve_control_product_for_complex(
        "shop",
        [10, 20],
        authoritative_control_nmid=30,
    )
    assert isinstance(result, ControlProductAmbiguous)
    assert result.reason == ProductControlBlockerReason.PRODUCT_CONTROL_MULTI_NM_AMBIGUOUS


def test_main_nmid_not_used_as_implicit_authority() -> None:
    nmids = [200, 100]
    main = sorted(nmids)[0]
    assert main_nmid_is_not_control_authority(main, nmids)
    resolved = resolve_control_product_for_complex("shop", nmids)
    assert isinstance(resolved, ControlProductAmbiguous)
