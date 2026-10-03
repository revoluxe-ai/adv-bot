"""Контрактные тесты generic strict single-NMID read-only audit."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from scripts.strict_single_nmid_audit import (
    ACTIONABLE,
    CONFIRMED,
    GAP,
    MISSING,
    NULL,
    PARTIAL,
    UNDEFINED,
    UNSUPPORTED,
    AuditIdentity,
    AuditPeriod,
    Evidence,
    MISSING_VALUE,
    ReadOnlyRunBudget,
    SpendEvidence,
    StrictAuditError,
    StrictSingleNmidAudit,
    build_human_summary,
    classify_value,
    derive_ratio,
    evidence,
    reconcile_physical_spend,
    validate_exact_identity,
    validate_output_contract,
)


IDENTITY = AuditIdentity(
    shop_id="5586b2ff-449c-4151-9518-60f46d32b7d9",
    cabinet=573,
    nmid=186069402,
    size_id=305698863,
    timezone="Europe/Moscow",
)


def test_pilot_identity_and_current_day_inclusive_period() -> None:
    """Точный pilot identity не расширяется, окно содержит текущий день."""
    period = AuditPeriod.current_day_inclusive(
        IDENTITY.timezone,
        now=datetime.fromisoformat("2026-09-19T18:08:00+03:00"),
    )

    assert IDENTITY.as_dict() == {
        "shop_id": "5586b2ff-449c-4151-9518-60f46d32b7d9",
        "cabinet": 573,
        "nmid": 186069402,
        "size_id": 305698863,
        "timezone": "Europe/Moscow",
    }
    assert period.start.isoformat() == "2026-09-06"
    assert period.end.isoformat() == "2026-09-19"
    assert period.days == 14


def test_identity_mismatch_is_fail_closed() -> None:
    """Любой mismatch shop/cabinet/NMID/size/timezone отклоняется."""
    actual = IDENTITY.as_dict()
    actual["nmid"] = 999

    with pytest.raises(StrictAuditError, match="identity mismatch"):
        validate_exact_identity(IDENTITY, actual)


def test_identity_mismatch_blocks_audit_decision() -> None:
    """Mismatch source identity переводит decision block в BLOCKED."""
    foreign_identity = AuditIdentity(
        shop_id=IDENTITY.shop_id,
        cabinet=IDENTITY.cabinet,
        nmid=999,
        size_id=IDENTITY.size_id,
        timezone=IDENTITY.timezone,
    )
    audit = StrictSingleNmidAudit(IDENTITY)

    result = audit.run(
        {
            "current_contour": lambda _identity, _period: [
                evidence(
                    foreign_identity,
                    "current_contour",
                    "auto",
                    {"id": 1},
                    source="authoritative-contour",
                )
            ]
        }
    )

    assert result["section_statuses"]["identity"] == "BLOCKED"
    assert result["decision"]["status"] == "BLOCKED"


def test_a1_or_unrelated_substitution_becomes_gap() -> None:
    """A1/fallback evidence не может silently закрыть strict audit section."""
    audit = StrictSingleNmidAudit(
        IDENTITY,
        now=datetime.fromisoformat("2026-09-19T18:08:00+03:00"),
    )

    def a1_reader(identity: AuditIdentity, period: AuditPeriod) -> list[Evidence]:
        del identity, period
        return [
            Evidence(
                section="current_contour",
                field="auto",
                identity=IDENTITY,
                status=CONFIRMED,
                value={"id": 1},
                source="A1 collector fallback",
            )
        ]

    result = audit.run({"current_contour": a1_reader})

    assert result["section_statuses"]["current_contour"] == GAP
    assert result["decision"]["status"] == PARTIAL
    assert any("forbidden" in gap for gap in result["decision"]["gaps"])


def test_unrelated_package_substitution_is_rejected() -> None:
    """Нерелевантный collector/package не становится silent source replacement."""
    audit = StrictSingleNmidAudit(IDENTITY)

    def unrelated_reader(identity: AuditIdentity, period: AuditPeriod) -> list[Evidence]:
        del identity, period
        return [
            Evidence(
                section="orders",
                field="orders",
                identity=IDENTITY,
                status=CONFIRMED,
                value=1,
                source="unrelated-package",
            )
        ]

    result = audit.run({"orders": unrelated_reader})

    assert result["section_statuses"]["orders"] == GAP
    assert any("substitution" in gap for gap in result["decision"]["gaps"])


def test_missing_null_unsupported_and_denominator_semantics_are_distinct() -> None:
    """Отсутствие, null, unsupported и denominator states не сводятся к нулю."""
    assert classify_value(0) == CONFIRMED
    assert classify_value(None) == NULL
    assert classify_value(None, present=False) == MISSING
    assert classify_value(None, supported=False) == UNSUPPORTED
    assert derive_ratio(10, 0)["value"] == UNDEFINED
    assert derive_ratio(10, None)["value"] == "NULL"
    assert derive_ratio(10, MISSING_VALUE)["value"] == UNDEFINED


def test_duplicate_physical_spend_is_counted_once() -> None:
    """Overlapping equal spend retains one canonical amount and provenance."""
    period = AuditPeriod(date(2026, 9, 6), date(2026, 9, 19), IDENTITY.timezone)
    records = [
        SpendEvidence(
            Decimal("12.50"),
            "fullstats",
            "campaign:42:2026-09-06..2026-09-19",
            IDENTITY,
            period,
        ),
        SpendEvidence(
            Decimal("12.50"),
            "campaign-total",
            "campaign:42:2026-09-06..2026-09-19",
            IDENTITY,
            period,
        ),
    ]

    result = reconcile_physical_spend(records, IDENTITY, period)

    assert result["status"] == CONFIRMED
    assert result["value"] == "12.50"
    assert result["overlap_sources"][0]["duplicate_sources"] == ["campaign-total"]


def test_conflicting_overlap_is_gap_not_glue_total() -> None:
    """Небезопасная reconciliation не складывает конкурирующие amounts."""
    period = AuditPeriod(date(2026, 9, 6), date(2026, 9, 19), IDENTITY.timezone)
    records = [
        SpendEvidence(10, "source-a", "same-physical-spend", IDENTITY, period),
        SpendEvidence(11, "source-b", "same-physical-spend", IDENTITY, period),
    ]

    result = reconcile_physical_spend(records, IDENTITY, period)

    assert result["status"] == GAP
    assert result["value"] is None


def _readers(identity: AuditIdentity, period: AuditPeriod) -> dict[str, object]:
    """Вернуть all-confirmed readers с accepted orders provenance."""
    return {
        "current_contour": lambda _i, _p: [
            evidence(identity, "current_contour", name, {"id": name}, source="wb-contour")
            for name in (
                "nmid_offer",
                "adv_setting",
                "auto",
                "search",
                "other_ids",
                "wb_statuses",
                "bot_settings",
                "cpo",
                "limits",
            )
        ],
        "orders": lambda _i, p: [
            evidence(
                identity,
                "orders",
                "orders",
                2,
                source="statistics-reports",
                provenance={
                    "family": "ORDERS_OR_SALES_REPORTS_READ",
                    "endpoint": "GET /api/v1/supplier/orders",
                    "period_attestation": p.as_dict(),
                },
                period=p,
            ),
            evidence(
                identity,
                "orders",
                "units",
                3,
                source="statistics-reports",
                provenance={
                    "family": "ORDERS_OR_SALES_REPORTS_READ",
                    "endpoint": "GET /api/v1/supplier/orders",
                    "period_attestation": p.as_dict(),
                },
                period=p,
            ),
            evidence(
                identity,
                "orders",
                "gmv",
                100,
                source="statistics-reports",
                provenance={
                    "family": "ORDERS_OR_SALES_REPORTS_READ",
                    "endpoint": "GET /api/v1/supplier/orders",
                    "period_attestation": p.as_dict(),
                },
                period=p,
            ),
        ],
        "attribution": lambda _i, p: [
            evidence(
                identity,
                "attribution",
                "direct",
                1,
                source="authoritative-attribution",
                provenance={"topology": "supported"},
                period=p,
                attribution_class="direct",
            ),
            evidence(
                identity,
                "attribution",
                "associated",
                1,
                source="authoritative-attribution",
                provenance={"topology": "supported"},
                period=p,
                attribution_class="associated",
            ),
        ],
        "topology": lambda _i, p: [
            evidence(
                identity,
                "topology",
                "association",
                "supported",
                source="authoritative-topology",
                period=p,
            )
        ],
        "stock": lambda _i, p: [
            evidence(identity, "stock", view, 1, source="stock-authority", period=p)
            for view in ("FBO", "FBS", "TOTAL")
        ],
        "physical_spend": lambda _i, p: [
            SpendEvidence(20, "canonical-spend", "physical:1", identity, p)
        ],
    }


def test_machine_human_contract_and_zero_write_budget() -> None:
    """Validated output keeps decision/statuses aligned and writes at zero."""
    audit = StrictSingleNmidAudit(
        IDENTITY,
        now=datetime.fromisoformat("2026-09-19T18:08:00+03:00"),
        budget=ReadOnlyRunBudget(max_calls=10, max_seconds=30),
    )

    result = audit.run(_readers(IDENTITY, audit.period))  # type: ignore[arg-type]

    validate_output_contract(result)
    assert result["decision"]["status"] == ACTIONABLE
    assert result["write_budget"]["writes"] == 0
    assert result["physical_spend"]["value"] == "20"
    assert "decision: ACTIONABLE" in build_human_summary(result)


def test_finite_call_budget_stops_reader_without_write_path() -> None:
    """Исчерпанный call budget даёт GAP и не создаёт production writes."""
    audit = StrictSingleNmidAudit(
        IDENTITY,
        budget=ReadOnlyRunBudget(max_calls=0, max_seconds=30),
    )

    result = audit.run(
        {
            "current_contour": lambda _identity, _period: pytest.fail(
                "reader must not run after budget exhaustion"
            )
        }
    )

    assert result["section_statuses"]["current_contour"] == GAP
    assert result["write_budget"]["writes"] == 0
    assert result["write_budget"]["calls_used"] == 0


def test_output_preserves_null_denominator_and_redacts_secrets() -> None:
    """Machine output сохраняет NULL denominator и secret-safe provenance."""
    audit = StrictSingleNmidAudit(IDENTITY)

    result = audit.run(
        {
            "orders": lambda identity, period: [
                evidence(
                    identity,
                    "orders",
                    "orders",
                    None,
                    source="statistics-reports",
                    provenance={
                        "family": "ORDERS_OR_SALES_REPORTS_READ",
                        "endpoint": "GET /api/v1/supplier/orders",
                        "period_attestation": period.as_dict(),
                        "api_token": "secret-value",
                    },
                    period=period,
                )
            ]
        }
    )

    assert result["totals"]["orders"]["status"] == NULL
    assert result["totals"]["cpo"]["value"] == "NULL"
    assert result["evidence"][0]["provenance"]["api_token"] == "<redacted>"
