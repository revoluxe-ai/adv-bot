"""Generic bounded single-NMID strict read-only audit.

Модуль содержит identity-safe orchestration и нормализацию evidence для
Owner-bot Job. Транспортные readers передаются вызывающим Job и должны
использовать существующий `app/core/mp/wb/api` access plane; этот модуль не
создаёт HTTP-клиент и не выполняет production writes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field as dataclass_field
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Protocol, TypeAlias, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from scripts.wb_api_readonly_ops.collect.owner_bot_evidence import (
    EvidenceImplementationFailure,
    EvidenceReaderFailure,
)

SCHEMA_VERSION: Final = "strict-single-nmid-audit-v1"
CONFIRMED: Final = "confirmed"
MISSING: Final = "missing"
NULL: Final = "null"
UNSUPPORTED: Final = "unsupported"
NONE: Final = "NONE"
GAP: Final = "GAP"
UNDEFINED: Final = "UNDEFINED"
ACTIONABLE: Final = "ACTIONABLE"
PARTIAL: Final = "PARTIAL"
BLOCKED: Final = "BLOCKED"

CURRENT_CONTOUR_FIELDS: Final[tuple[str, ...]] = (
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
STOCK_VIEWS: Final[tuple[str, ...]] = ("FBO", "FBS", "TOTAL")
ORDERS_ENDPOINTS: Final[frozenset[str]] = frozenset(
    {
        "GET /api/v1/supplier/orders",
        "GET /api/v1/supplier/sales",
    }
)
FORBIDDEN_SOURCE_MARKERS: Final[frozenset[str]] = frozenset(
    {"a1", "unrelated", "fallback", "substitution"}
)


def _empty_provenance() -> dict[str, Any]:
    """Создать типизированный пустой provenance mapping для dataclass."""
    return {}


_SECRET_KEY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(token|secret|password|authorization|cookie|api[_-]?key)"
)


def _secret_safe(value: Any) -> Any:
    """Удалить credentials из nested evidence перед локальным output."""
    if isinstance(value, Mapping):
        mapping = cast(Mapping[Any, Any], value)
        return {
            str(key): "<redacted>" if _SECRET_KEY_RE.search(str(key)) else _secret_safe(item)
            for key, item in mapping.items()
        }
    if isinstance(value, list):
        return [_secret_safe(item) for item in cast(list[Any], value)]
    if isinstance(value, tuple):
        return [_secret_safe(item) for item in cast(tuple[Any, ...], value)]
    if isinstance(value, str):
        return re.sub(
            r"(?i)(token|secret|password|authorization|cookie)\s*[=:]\s*\S+",
            r"\1=<redacted>",
            value,
        )
    return value


class StrictAuditError(ValueError):
    """Ошибка fail-closed валидации identity, evidence или output contract."""


class RunBudgetExceeded(StrictAuditError):
    """Источник превысил конечный budget вызовов или времени."""


@dataclass(frozen=True)
class AuditIdentity:
    """Неизменяемая identity одного audit target.

    Args:
        shop_id: Точный идентификатор магазина/access-plane tenant.
        cabinet: Точный WB cabinet identifier.
        nmid: Единственный целевой NMID.
        size_id: Точный client size identifier.
        timezone: IANA timezone для календарного окна.
    """

    shop_id: str
    cabinet: int
    nmid: int
    size_id: int
    timezone: str = "Europe/Moscow"

    def __post_init__(self) -> None:
        """Проверить обязательные positive identifiers и timezone."""
        if not self.shop_id.strip():
            raise StrictAuditError("shop_id must be non-empty")
        for name, value in (
            ("cabinet", self.cabinet),
            ("nmid", self.nmid),
            ("size_id", self.size_id),
        ):
            if isinstance(value, bool) or value <= 0:
                raise StrictAuditError(f"{name} must be a positive integer")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise StrictAuditError(f"unknown timezone: {self.timezone}") from exc

    def as_dict(self) -> dict[str, Any]:
        """Вернуть machine-readable identity без widening или fallback."""
        return {
            "shop_id": self.shop_id,
            "cabinet": self.cabinet,
            "nmid": self.nmid,
            "size_id": self.size_id,
            "timezone": self.timezone,
        }


@dataclass(frozen=True)
class AuditPeriod:
    """Точное inclusive календарное окно в timezone audit identity."""

    start: date
    end: date
    timezone: str

    def __post_init__(self) -> None:
        """Проверить порядок дат, timezone и календарную длину."""
        if self.start > self.end:
            raise StrictAuditError("period start must not be after end")
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise StrictAuditError(f"unknown timezone: {self.timezone}") from exc

    @classmethod
    def current_day_inclusive(
        cls,
        timezone_name: str,
        *,
        now: datetime | None = None,
        days: int = 14,
    ) -> AuditPeriod:
        """Построить окно из текущего локального дня и 13 предыдущих.

        Args:
            timezone_name: IANA timezone входной identity.
            now: Текущее время; injectable для deterministic tests.
            days: Число календарных дней, строго положительное.
        """
        if days <= 0:
            raise StrictAuditError("period days must be positive")
        try:
            zone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise StrictAuditError(f"unknown timezone: {timezone_name}") from exc
        local_now = (now or datetime.now(zone)).astimezone(zone)
        end = local_now.date()
        return cls(start=end - timedelta(days=days - 1), end=end, timezone=timezone_name)

    @property
    def days(self) -> int:
        """Вернуть количество inclusive календарных дней окна."""
        return (self.end - self.start).days + 1

    def as_dict(self) -> dict[str, Any]:
        """Вернуть период для machine-readable output."""
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "days": self.days,
            "timezone": self.timezone,
            "inclusive": True,
        }


def validate_exact_identity(
    expected: AuditIdentity, actual: Mapping[str, Any]
) -> None:
    """Fail-closed проверить exact shop/cabinet/NMID/size/timezone tuple.

    Raises:
        StrictAuditError: если source payload отсутствует или расходится.
    """
    expected_values = expected.as_dict()
    missing = [key for key in expected_values if key not in actual]
    if missing:
        raise StrictAuditError(f"identity fields missing: {', '.join(missing)}")
    mismatches = [
        f"{key}: expected={expected_values[key]!r}, got={actual[key]!r}"
        for key in expected_values
        if str(actual[key]) != str(expected_values[key])
    ]
    if mismatches:
        raise StrictAuditError("identity mismatch: " + "; ".join(mismatches))


def classify_value(
    value: Any,
    *,
    present: bool = True,
    supported: bool = True,
    complete: bool = True,
) -> str:
    """Классифицировать наблюдение без превращения отсутствия в numeric zero."""
    if not supported:
        return UNSUPPORTED
    if not present:
        return MISSING
    if value is None:
        return NULL
    if not complete:
        return GAP
    return CONFIRMED


@dataclass(frozen=True)
class Evidence:
    """Один provenance-aware факт для exact audit identity."""

    section: str
    field: str
    identity: AuditIdentity
    status: str
    value: Any = None
    source: str = ""
    provenance: Mapping[str, Any] = dataclass_field(default_factory=_empty_provenance)
    period: AuditPeriod | None = None
    attribution_class: str | None = None
    source_class: str = "authoritative"
    fallback_used: bool = False

    def __post_init__(self) -> None:
        """Проверить status и запретить не-authoritative routing."""
        allowed = {
            CONFIRMED,
            MISSING,
            NULL,
            UNSUPPORTED,
            NONE,
            GAP,
            UNDEFINED,
        }
        if self.status not in allowed:
            raise StrictAuditError(f"unknown evidence status: {self.status}")
        if self.source_class != "authoritative" or self.fallback_used:
            raise StrictAuditError("non-authoritative or fallback evidence is forbidden")
        marker_text = self.source.lower()
        if any(marker in marker_text for marker in FORBIDDEN_SOURCE_MARKERS):
            raise StrictAuditError("A1/unrelated/fallback source substitution is forbidden")
        for key in ("source_kind", "collector", "package"):
            value = str(self.provenance.get(key, "")).lower()
            if any(marker in value for marker in FORBIDDEN_SOURCE_MARKERS):
                raise StrictAuditError(
                    "A1/unrelated/fallback source substitution is forbidden"
                )
        if self.attribution_class not in (None, "direct", "associated"):
            raise StrictAuditError("attribution_class must be direct or associated")
        if self.period is not None and self.period.timezone != self.identity.timezone:
            raise StrictAuditError("evidence timezone differs from audit identity")

    def as_dict(self) -> dict[str, Any]:
        """Сериализовать факт, сохраняя provenance и explicit status."""
        return {
            "section": self.section,
            "field": self.field,
            "identity": self.identity.as_dict(),
            "status": self.status,
            "value": _secret_safe(self.value),
            "source": self.source,
            "provenance": _secret_safe(dict(self.provenance)),
            "period": self.period.as_dict() if self.period else None,
            "attribution_class": self.attribution_class,
        }


def evidence(
    identity: AuditIdentity,
    section: str,
    field_name: str,
    value: Any,
    *,
    source: str,
    provenance: Mapping[str, Any] | None = None,
    period: AuditPeriod | None = None,
    present: bool = True,
    supported: bool = True,
    complete: bool = True,
    attribution_class: str | None = None,
) -> Evidence:
    """Создать нормализованный факт с честной missing/null/unsupported семантикой."""
    return Evidence(
        section=section,
        field=field_name,
        identity=identity,
        status=classify_value(
            value, present=present, supported=supported, complete=complete
        ),
        value=value,
        source=source,
        provenance=dict(provenance) if provenance is not None else {},
        period=period,
        attribution_class=attribution_class,
    )


@dataclass(frozen=True)
class SpendEvidence:
    """Physical spend с обязательным explicit overlap key."""

    amount: Decimal | int | float | None
    source: str
    overlap_key: str | None
    identity: AuditIdentity
    period: AuditPeriod
    provenance: Mapping[str, Any] = dataclass_field(default_factory=_empty_provenance)
    status: str = CONFIRMED

    def as_dict(self) -> dict[str, Any]:
        """Сериализовать spend evidence для reconciliation provenance."""
        return {
            "amount": str(self.amount) if self.amount is not None else None,
            "source": self.source,
            "overlap_key": self.overlap_key,
            "identity": self.identity.as_dict(),
            "period": self.period.as_dict(),
            "provenance": _secret_safe(dict(self.provenance)),
            "status": self.status,
        }


def _decimal(value: Decimal | int | float | str) -> Decimal:
    """Безопасно привести сумму к Decimal без float arithmetic."""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise StrictAuditError(f"invalid numeric value: {value!r}") from exc


def reconcile_physical_spend(
    records: Iterable[SpendEvidence], identity: AuditIdentity, period: AuditPeriod
) -> dict[str, Any]:
    """Выбрать одну canonical spend representation без physical double count.

    Equal amounts sharing an explicit overlap key are retained once. Conflicting
    amounts or missing keys produce GAP instead of glue inference.
    """
    items = list(records)
    if not items:
        return {
            "status": MISSING,
            "value": None,
            "currency": "RUB",
            "canonical_sources": [],
            "overlap_sources": [],
            "gaps": ["physical spend evidence is missing"],
        }
    for item in items:
        try:
            validate_exact_identity(identity, item.identity.as_dict())
        except StrictAuditError as exc:
            return {
                "status": GAP,
                "value": None,
                "currency": "RUB",
                "canonical_sources": [],
                "overlap_sources": [],
                "gaps": [str(exc)],
            }
        if item.period != period or not item.overlap_key:
            return {
                "status": GAP,
                "value": None,
                "currency": "RUB",
                "canonical_sources": [],
                "overlap_sources": [],
                "gaps": ["spend period or explicit overlap_key is unsafe"],
            }
        if item.status != CONFIRMED or item.amount is None:
            return {
                "status": GAP,
                "value": None,
                "currency": "RUB",
                "canonical_sources": [],
                "overlap_sources": [],
                "gaps": [f"spend source {item.source} is {item.status}"],
            }
    grouped: dict[str, list[SpendEvidence]] = defaultdict(list)
    for item in items:
        grouped[item.overlap_key or ""].append(item)
    total = Decimal("0")
    canonical_sources: list[str] = []
    overlap_sources: list[dict[str, Any]] = []
    for overlap_key, group in grouped.items():
        amounts = {_decimal(item.amount or 0) for item in group}
        if len(amounts) != 1:
            return {
                "status": GAP,
                "value": None,
                "currency": "RUB",
                "canonical_sources": [],
                "overlap_sources": overlap_sources,
                "gaps": [f"conflicting overlapping spend for {overlap_key}"],
            }
        amount = next(iter(amounts))
        total += amount
        canonical_sources.append(group[0].source)
        if len(group) > 1:
            overlap_sources.append(
                {
                    "overlap_key": overlap_key,
                    "canonical_source": group[0].source,
                    "duplicate_sources": [item.source for item in group[1:]],
                    "amount": str(amount),
                }
            )
    return {
        "status": CONFIRMED,
        "value": str(total),
        "currency": "RUB",
        "canonical_sources": canonical_sources,
        "overlap_sources": overlap_sources,
        "gaps": [],
    }


MISSING_VALUE: Final[object] = object()


def derive_ratio(numerator: Any, denominator: Any) -> dict[str, Any]:
    """Рассчитать derived metric с явным NULL/UNDEFINED denominator state."""
    if denominator is MISSING_VALUE:
        return {"value": UNDEFINED, "status": UNDEFINED, "denominator": MISSING}
    if denominator is None:
        return {"value": "NULL", "status": NULL, "denominator": NULL}
    denominator_decimal = _decimal(denominator)
    if denominator_decimal == 0:
        return {"value": UNDEFINED, "status": UNDEFINED, "denominator": "zero"}
    if numerator is MISSING_VALUE:
        return {"value": UNDEFINED, "status": UNDEFINED, "denominator": CONFIRMED}
    if numerator is None:
        return {"value": "NULL", "status": NULL, "denominator": CONFIRMED}
    value = _decimal(numerator) / denominator_decimal
    return {
        "value": str(value.normalize()),
        "status": CONFIRMED,
        "denominator": CONFIRMED,
    }


@dataclass
class ReadOnlyRunBudget:
    """Конечный whole-run budget для Owner-bot Job orchestration."""

    max_calls: int = 50
    max_seconds: float = 900.0
    calls_used: int = 0
    _started_at: float = dataclass_field(default_factory=time.monotonic, init=False)

    def consume(self) -> None:
        """Зарезервировать один reader call или остановить source."""
        if self.calls_used >= self.max_calls:
            raise RunBudgetExceeded("read-only call budget exhausted")
        if time.monotonic() - self._started_at >= self.max_seconds:
            raise RunBudgetExceeded("read-only time budget exhausted")
        self.calls_used += 1


EvidenceReader: TypeAlias = Callable[
    [AuditIdentity, AuditPeriod], Iterable[Evidence | SpendEvidence]
]


class OwnerBotReadOnlyPlane(Protocol):
    """Контракт адаптера над существующим Owner-bot/app WB API stack.

    Реализация создаётся только Job runtime через access plane по `shop_id`.
    Методы не должны выполнять mutation; unsupported capability возвращает
    пустой iterable или evidence с соответствующим status.
    """

    def read_current_contour(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать NMID/OFFER, AdvSetting, Auto/Search, statuses/settings."""
        ...

    def read_orders(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать orders/units/GMV через Reports identity."""
        ...

    def read_attribution(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать отдельные direct/associated attribution facts."""
        ...

    def read_topology(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать только authoritative topology."""
        ...

    def read_stock(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать FBO/FBS/TOTAL stock или вернуть explicit gap."""
        ...

    def read_physical_spend(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[SpendEvidence]:
        """Прочитать physical spend с explicit overlap keys."""
        ...


def readers_from_owner_bot_plane(
    plane: OwnerBotReadOnlyPlane,
) -> dict[str, EvidenceReader]:
    """Связать Job access plane с generic audit без raw HTTP или fallback."""
    return {
        "current_contour": plane.read_current_contour,
        "orders": plane.read_orders,
        "attribution": plane.read_attribution,
        "topology": plane.read_topology,
        "stock": plane.read_stock,
        "physical_spend": plane.read_physical_spend,
    }


def _attribute_error_is_mapping_shape(exc: AttributeError) -> bool:
    """True если ``AttributeError`` похож на ``.get()`` по non-dict bundle entry."""
    message = str(exc)
    return "has no attribute 'get'" in message or ".get" in message


def _gap_line_for_attribute_error(section: str, exc: AttributeError) -> str:
    """Сформировать gap line: implementation shape vs unknown AttributeError."""
    if _attribute_error_is_mapping_shape(exc):
        return (
            f"{section}: AttributeError phase=implementation_shape "
            f"implementation_shape=1 message={exc}"
        )
    return f"{section}: AttributeError"


def _collect_spend_records(
    raw_items: list[Evidence | SpendEvidence],
    evidence_items: list[Evidence],
    identity: AuditIdentity,
    period: AuditPeriod,
) -> list[SpendEvidence]:
    """Собрать spend records для reconcile (SpendEvidence + projected Evidence)."""
    spends = [item for item in raw_items if isinstance(item, SpendEvidence)]
    if spends:
        return spends
    projected: list[SpendEvidence] = []
    for item in evidence_items:
        if item.section != "physical_spend" or item.field != "physical_spend":
            continue
        if item.status not in {CONFIRMED, GAP} or item.value is None:
            continue
        overlap_key = item.provenance.get("overlap_key")
        if not isinstance(overlap_key, str) or not overlap_key:
            continue
        try:
            amount = Decimal(str(item.value))
        except (InvalidOperation, ValueError):
            continue
        projected.append(
            SpendEvidence(
                amount=amount,
                source=item.source,
                overlap_key=overlap_key,
                identity=identity,
                period=period,
                provenance=dict(item.provenance),
                status=item.status,
            )
        )
    return projected


def _as_evidence(
    value: Evidence | SpendEvidence, identity: AuditIdentity, period: AuditPeriod
) -> Evidence:
    """Преобразовать SpendEvidence в section evidence для общего output."""
    if isinstance(value, Evidence):
        validate_exact_identity(identity, value.identity.as_dict())
        if value.period is not None and value.period != period:
            raise StrictAuditError("evidence period differs from audit period")
        return value
    validate_exact_identity(identity, value.identity.as_dict())
    return evidence(
        identity,
        "physical_spend",
        "physical_spend",
        str(value.amount) if value.amount is not None else None,
        source=value.source,
        provenance={**value.provenance, "overlap_key": value.overlap_key},
        period=period,
        present=value.amount is not None,
        supported=value.status != UNSUPPORTED,
        complete=value.status == CONFIRMED,
    )


def _validate_orders_evidence(item: Evidence) -> None:
    """Проверить accepted ORDERS_OR_SALES_REPORTS_READ identity."""
    if item.section != "orders":
        return
    family = item.provenance.get("family")
    endpoint = item.provenance.get("endpoint")
    if family != "ORDERS_OR_SALES_REPORTS_READ" or endpoint not in ORDERS_ENDPOINTS:
        raise StrictAuditError("orders evidence is not authoritative Reports identity")
    if not item.provenance.get("period_attestation"):
        raise StrictAuditError("orders evidence lacks honest period attestation")


def _section_status(items: list[Evidence]) -> str:
    """Получить aggregate status, не скрывая любой GAP."""
    if not items:
        return UNSUPPORTED
    statuses = {item.status for item in items}
    if GAP in statuses or NONE in statuses:
        return GAP
    if statuses <= {CONFIRMED}:
        return CONFIRMED
    return PARTIAL


def _decision_status(section_statuses: Mapping[str, str], gaps: list[str]) -> str:
    """Сформировать decision state без рекомендации владельцу."""
    if "identity" in section_statuses and section_statuses["identity"] != CONFIRMED:
        return BLOCKED
    if gaps or any(
        value in {GAP, MISSING, UNSUPPORTED, PARTIAL, NULL}
        for value in section_statuses.values()
    ):
        return PARTIAL
    return ACTIONABLE


def validate_output_contract(payload: Mapping[str, Any]) -> None:
    """Проверить минимальный versioned machine-readable output contract."""
    required = {
        "schema_version",
        "identity",
        "period",
        "sections",
        "section_statuses",
        "evidence",
        "physical_spend",
        "totals",
        "stock",
        "decision",
        "write_budget",
    }
    missing = sorted(required - set(payload))
    if missing:
        raise StrictAuditError(f"output contract fields missing: {missing}")
    identity = payload["identity"]
    if not isinstance(identity, Mapping):
        raise StrictAuditError("output identity must be an object")
    identity_values: Mapping[str, Any] = cast(Mapping[str, Any], identity)
    validate_exact_identity(
        AuditIdentity(
            shop_id=str(identity_values["shop_id"]),
            cabinet=int(identity_values["cabinet"]),
            nmid=int(identity_values["nmid"]),
            size_id=int(identity_values["size_id"]),
            timezone=str(identity_values["timezone"]),
        ),
        identity_values,
    )
    if payload["write_budget"].get("writes") != 0:
        raise StrictAuditError("strict audit output has non-zero writes")
    decision = payload["decision"]
    if decision.get("status") not in {ACTIONABLE, PARTIAL, BLOCKED}:
        raise StrictAuditError("decision status is invalid")
    for item in payload["evidence"]:
        evidence_identity: Mapping[str, Any] = cast(
            Mapping[str, Any], item["identity"]
        )
        validate_exact_identity(
            AuditIdentity(
                shop_id=str(evidence_identity["shop_id"]),
                cabinet=int(evidence_identity["cabinet"]),
                nmid=int(evidence_identity["nmid"]),
                size_id=int(evidence_identity["size_id"]),
                timezone=str(evidence_identity["timezone"]),
            ),
            evidence_identity,
        )


def build_human_summary(payload: Mapping[str, Any]) -> str:
    """Построить concise summary только из уже normalized machine facts."""
    validate_output_contract(payload)
    identity = payload["identity"]
    period = payload["period"]
    decision = payload["decision"]
    lines = [
        "STRICT SINGLE-NMID READ-ONLY AUDIT",
        (
            "identity: "
            f"shop={identity['shop_id']} cabinet={identity['cabinet']} "
            f"nmid={identity['nmid']} size={identity['size_id']} "
            f"timezone={identity['timezone']}"
        ),
        (
            f"period: {period['start']}..{period['end']} "
            f"({period['days']} calendar days, inclusive)"
        ),
        f"decision: {decision['status']}",
        "section_statuses: "
        + json.dumps(payload["section_statuses"], ensure_ascii=False, sort_keys=True),
        "gaps: " + json.dumps(decision["gaps"], ensure_ascii=False),
        "writes: 0",
    ]
    return "\n".join(lines)


class StrictSingleNmidAudit:
    """Оркестратор bounded evidence readers для одного exact NMID.

    Readers принадлежат Job runtime и отвечают за вызовы существующего
    Owner-bot/WB API stack. Оркестратор нормализует их результат, применяет
    identity/fallback gates и формирует единый machine/human output.
    """

    def __init__(
        self,
        identity: AuditIdentity,
        *,
        now: datetime | None = None,
        days: int = 14,
        budget: ReadOnlyRunBudget | None = None,
    ) -> None:
        """Создать audit с current-day-inclusive period и finite budget."""
        self.identity = identity
        self.period = AuditPeriod.current_day_inclusive(
            identity.timezone, now=now, days=days
        )
        self.budget = budget or ReadOnlyRunBudget()

    def run(self, readers: Mapping[str, EvidenceReader]) -> dict[str, Any]:
        """Собрать sections и вернуть validated read-only result.

        Args:
            readers: Section readers из Owner-bot Job. Допустимые sections:
                current_contour, orders, attribution, topology, stock,
                physical_spend.
        """
        raw_items: list[Evidence | SpendEvidence] = []
        gaps: list[str] = []
        section_statuses: dict[str, str] = {"identity": CONFIRMED}
        for section in (
            "current_contour",
            "orders",
            "attribution",
            "topology",
            "stock",
            "physical_spend",
        ):
            reader = readers.get(section)
            if reader is None:
                section_statuses[section] = UNSUPPORTED
                gaps.append(f"{section}: reader is not configured")
                continue
            try:
                self.budget.consume()
                values = list(reader(self.identity, self.period))
                normalized: list[Evidence] = []
                for value in values:
                    item = _as_evidence(value, self.identity, self.period)
                    _validate_orders_evidence(item)
                    normalized.append(item)
                    raw_items.append(value)
                section_statuses[section] = _section_status(normalized)
                if not normalized:
                    gaps.append(f"{section}: no evidence returned")
            except EvidenceReaderFailure as exc:
                if exc.section == "identity" or "identity mismatch" in str(exc):
                    section_statuses["identity"] = BLOCKED
                section_statuses[section] = GAP
                gaps.append(
                    f"{section}: {exc.error_class} source={exc.source} phase={exc.phase}"
                )
            except EvidenceImplementationFailure as exc:
                section_statuses[section] = GAP
                gaps.append(
                    f"{section}: {exc.error_class} phase={exc.phase} "
                    f"implementation_shape=1 message={exc.message}"
                )
            except (RunBudgetExceeded, StrictAuditError) as exc:
                if "identity mismatch" in str(exc):
                    section_statuses["identity"] = BLOCKED
                section_statuses[section] = GAP
                gaps.append(f"{section}: {exc}")
            except AttributeError as exc:
                section_statuses[section] = GAP
                gaps.append(_gap_line_for_attribute_error(section, exc))
            except Exception as exc:  # noqa: BLE001 — source becomes explicit GAP
                section_statuses[section] = GAP
                gaps.append(f"{section}: {type(exc).__name__}")

        evidence_items = [
            _as_evidence(item, self.identity, self.period) for item in raw_items
        ]
        spend_records = _collect_spend_records(
            raw_items, evidence_items, self.identity, self.period
        )
        spend = reconcile_physical_spend(spend_records, self.identity, self.period)
        if spend["status"] != CONFIRMED:
            gaps.extend(spend["gaps"])
        section_statuses["physical_spend"] = (
            CONFIRMED if spend["status"] == CONFIRMED else spend["status"]
        )

        present_fields = {
            item.field
            for item in raw_items
            if isinstance(item, Evidence) and item.section == "current_contour"
        }
        for field_name in CURRENT_CONTOUR_FIELDS:
            if field_name not in present_fields:
                raw_items.append(
                    Evidence(
                        section="current_contour",
                        field=field_name,
                        identity=self.identity,
                        status=NONE,
                        source="strict-audit-normalizer",
                        provenance={"reason": "no authoritative evidence"},
                        period=self.period,
                    )
                )
                gaps.append(f"current_contour.{field_name}: NONE")

        attribution_fields = {
            item.field
            for item in raw_items
            if isinstance(item, Evidence) and item.section == "attribution"
        }
        for field_name in ("direct", "associated"):
            if field_name not in attribution_fields:
                raw_items.append(
                    Evidence(
                        section="attribution",
                        field=field_name,
                        identity=self.identity,
                        status=GAP,
                        source="strict-audit-normalizer",
                        provenance={"reason": "authoritative association not evidenced"},
                        period=self.period,
                    )
                )
                gaps.append(f"attribution.{field_name}: GAP")

        if not any(
            isinstance(item, Evidence) and item.section == "topology"
            for item in raw_items
        ):
            raw_items.append(
                Evidence(
                    section="topology",
                    field="topology",
                    identity=self.identity,
                    status=GAP,
                    source="strict-audit-normalizer",
                    provenance={"reason": "authoritative topology not evidenced"},
                    period=self.period,
                )
            )
            gaps.append("topology: GAP")
        section_statuses["current_contour"] = _section_status(
            [
                _as_evidence(item, self.identity, self.period)
                for item in raw_items
                if isinstance(item, Evidence) and item.section == "current_contour"
            ]
        )
        section_statuses["attribution"] = _section_status(
            [
                _as_evidence(item, self.identity, self.period)
                for item in raw_items
                if isinstance(item, Evidence) and item.section == "attribution"
            ]
        )
        section_statuses["topology"] = _section_status(
            [
                _as_evidence(item, self.identity, self.period)
                for item in raw_items
                if isinstance(item, Evidence) and item.section == "topology"
            ]
        )

        stock: dict[str, Any] = {}
        for view in STOCK_VIEWS:
            matches = [
                item
                for item in evidence_items
                if item.section == "stock" and item.field.upper() == view
            ]
            stock[view] = matches[0].as_dict() if matches else {
                "status": GAP,
                "value": None,
                "reason": "authoritative stock view not evidenced",
            }

        totals: dict[str, Any] = {}
        for field_name in ("orders", "units", "gmv"):
            matches = [
                item
                for item in evidence_items
                if item.field == field_name
            ]
            if not matches:
                totals[field_name] = {"status": MISSING, "value": None}
            else:
                item = matches[0]
                totals[field_name] = {"status": item.status, "value": item.value}
        orders_state = totals["orders"]
        gmv_state = totals["gmv"]
        orders_denominator: Any = MISSING_VALUE
        gmv_denominator: Any = MISSING_VALUE
        if orders_state["status"] == CONFIRMED:
            orders_denominator = orders_state["value"]
        elif orders_state["status"] == NULL:
            orders_denominator = None
        if gmv_state["status"] == CONFIRMED:
            gmv_denominator = gmv_state["value"]
        elif gmv_state["status"] == NULL:
            gmv_denominator = None
        totals["cpo"] = derive_ratio(
            spend["value"] if spend["status"] == CONFIRMED else MISSING_VALUE,
            orders_denominator,
        )
        totals["drr"] = derive_ratio(
            spend["value"] if spend["status"] == CONFIRMED else MISSING_VALUE,
            gmv_denominator,
        )
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "identity": self.identity.as_dict(),
            "period": self.period.as_dict(),
            "sections": {
                "current_contour": list(CURRENT_CONTOUR_FIELDS),
                "attribution": ["direct", "associated"],
                "stock": list(STOCK_VIEWS),
            },
            "section_statuses": section_statuses,
            "evidence": [item.as_dict() for item in evidence_items],
            "physical_spend": {**spend, "evidence": [item.as_dict() for item in spend_records]},
            "totals": totals,
            "stock": stock,
            "decision": {
                "status": _decision_status(section_statuses, gaps),
                "confirmed_facts": [
                    section
                    for section, status in section_statuses.items()
                    if status == CONFIRMED
                ],
                "gaps": sorted(set(gaps)),
                "recommendations": [],
            },
            "write_budget": {"writes": 0, "max_calls": self.budget.max_calls, "calls_used": self.budget.calls_used},
        }
        validate_output_contract(payload)
        payload["human_summary"] = build_human_summary(payload)
        return payload


def write_output(payload: Mapping[str, Any], path: Path) -> None:
    """Записать только локальный UTF-8 machine-readable artifact."""
    validate_output_contract(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def is_owner_bot_job_runtime() -> bool:
    """True только внутри Kubernetes Owner-bot Job pod."""
    return os.environ.get("KUBERNETES_SERVICE_HOST", "").strip() != ""


def run_owner_bot_job(args: argparse.Namespace) -> dict[str, Any]:
    """Собрать audit через injected Owner-bot read-only plane и записать output.

    Raises:
        StrictAuditError: при нарушении identity/output contract.
    """
    from scripts.set_path import add_project_root_to_path
    from scripts.strict_single_nmid_audit_owner_bot_plane import (
        build_owner_bot_read_only_plane,
    )

    add_project_root_to_path()
    identity = AuditIdentity(
        shop_id=args.shop_id,
        cabinet=args.cabinet,
        nmid=args.nmid,
        size_id=args.size_id,
        timezone=args.timezone,
    )
    plane = build_owner_bot_read_only_plane()
    audit = StrictSingleNmidAudit(identity)
    try:
        plane.ensure_bundle(identity, audit.period)
        payload = audit.run(readers_from_owner_bot_plane(plane))
    finally:
        plane.close()
    write_output(payload, args.output)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    sidecar = args.output.with_suffix(args.output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    payload["primary_artifact_sha256"] = digest
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Разобрать identity и bounded Job output arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--cabinet", required=True, type=int)
    parser.add_argument("--nmid", required=True, type=int)
    parser.add_argument("--size-id", required=True, type=int)
    parser.add_argument("--timezone", default="Europe/Moscow")
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Job runtime injects Owner-bot readers; local bare execution fail-closed."""
    args = parse_args(argv)
    if not is_owner_bot_job_runtime():
        print(
            "Owner-bot Job must inject existing WB/API readers; local execution is refused",
            file=sys.stderr,
        )
        return 1
    try:
        payload = run_owner_bot_job(args)
    except StrictAuditError as exc:
        print(f"strict-single-nmid-audit failed: {exc}", file=sys.stderr)
        return 1
    digest = str(payload.get("primary_artifact_sha256", ""))
    if digest:
        print(f"PRIMARY_SHA256={digest}")
    print("ops-script: success; holding for output copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
