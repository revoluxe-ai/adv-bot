"""Unit: CLI modes и overall status honesty (INC-RO-01)."""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.unit

from scripts.wb_api_readonly_ops.cli import parse_args
from scripts.wb_api_readonly_ops.models import (
    FamilyName,
    FamilyResult,
    FamilyStatus,
    OverallStatus,
    compute_overall_status,
)


def test_cli_requires_shop_id_and_mode() -> None:
    """Неизвестный mode → SystemExit; валидные args парсятся."""
    with pytest.raises(SystemExit) as exc:
        parse_args([])
    assert exc.value.code != 0

    with pytest.raises(SystemExit) as exc2:
        parse_args(["--shop-id", "abc", "--mode", "mutate"])
    assert exc2.value.code != 0

    ns = parse_args(["--shop-id", "abc", "--mode", "preflight"])
    assert ns.shop_id == "abc"
    assert ns.mode == "preflight"
    # ORDERS default dateFrom = pilot 2026-07-04 (not yesterday→today)
    assert ns.orders_date_from == "2026-07-04"

    ns2 = parse_args(["--shop-id", "abc", "--mode", "collect"])
    assert ns2.mode == "collect"

    ns3 = parse_args(
        [
            "--shop-id",
            "abc",
            "--mode",
            "preflight",
            "--orders-date-from",
            "2026-07-10",
        ]
    )
    assert ns3.orders_date_from == "2026-07-10"


def test_overall_not_ok_when_family_gaps() -> None:
    """Full success запрещён при gaps / PARTIAL / FAILED."""
    families = [
        FamilyResult(family=FamilyName.ADS, status=FamilyStatus.OK),
        FamilyResult(
            family=FamilyName.CARDS,
            status=FamilyStatus.PARTIAL,
            gaps=["missing page"],
        ),
        FamilyResult(family=FamilyName.ANALYTICS, status=FamilyStatus.OK),
        FamilyResult(family=FamilyName.NORMS, status=FamilyStatus.OK),
    ]
    assert compute_overall_status(families) == OverallStatus.PARTIAL

    all_ok = [
        FamilyResult(family=f, status=FamilyStatus.OK) for f in FamilyName
    ]
    assert compute_overall_status(all_ok) == OverallStatus.OK

    with_gap_note = [
        FamilyResult(
            family=FamilyName.ADS,
            status=FamilyStatus.OK,
            gaps=["silent gap"],
        ),
        FamilyResult(family=FamilyName.CARDS, status=FamilyStatus.OK),
        FamilyResult(family=FamilyName.ANALYTICS, status=FamilyStatus.OK),
        FamilyResult(family=FamilyName.NORMS, status=FamilyStatus.OK),
    ]
    assert compute_overall_status(with_gap_note) == OverallStatus.PARTIAL
