"""Owner-bot Job access plane для strict single-NMID read-only audit.

Адаптер реализует ``OwnerBotReadOnlyPlane`` поверх shared evidence loader
(``scripts.wb_api_readonly_ops.collect.owner_bot_evidence``) и existing
Owner-bot access plane. Новый raw HTTP-клиент не создаётся.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from scripts.strict_single_nmid_audit import (
    CONFIRMED,
    GAP,
    AuditIdentity,
    AuditPeriod,
    Evidence,
    SpendEvidence,
    evidence,
)
from scripts.wb_api_readonly_ops.collect.owner_bot_evidence import (
    EvidenceReaderFailure,
    JobScopedEvidenceRuntime,
    OwnerBotEvidenceBundle,
    load_owner_bot_evidence_bundle,
)

# Backward-compatible alias для unit tests.
_Bundle = OwnerBotEvidenceBundle


def _read_int(row: dict[str, Any], *names: str) -> int:
    """Вернуть первое положительное целое из WB/PG aliases."""
    for name in names:
        value = row.get(name)
        if value in (None, ""):
            continue
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return 0


def _read_number(row: dict[str, Any], *names: str) -> float | None:
    """Вернуть первое числовое поле или ``None``."""
    for name in names:
        value = row.get(name)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _parse_nmids(raw: Any) -> set[int]:
    """Разобрать nmids из PG ``advsetting.nmids`` без расширения scope."""
    return {int(match) for match in re.findall(r"\d+", str(raw or ""))}


def _parse_day(value: Any) -> date | None:
    """Нормализовать ISO date/datetime к календарному дню."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value)
    try:
        if "T" in text or " " in text:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        return date.fromisoformat(text[:10])
    except (TypeError, ValueError):
        return None


def _row_day(row: dict[str, Any]) -> date | None:
    """Извлечь календарный день supplier row."""
    for key in ("date", "lastChangeDate", "orderDate"):
        parsed = _parse_day(row.get(key))
        if parsed is not None:
            return parsed
    return None


def _is_cancel(row: dict[str, Any]) -> bool:
    return str(row.get("isCancel", "")).lower() in {"true", "1", "t"}


def _orders_attestation(period: AuditPeriod, rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Честная period attestation по фактическим датам supplier orders."""
    days = sorted({day.isoformat() for day in (_row_day(row) for row in rows) if day})
    covered_start = days[0] if days else None
    covered_end = days[-1] if days else None
    return {
        "family": "ORDERS_OR_SALES_REPORTS_READ",
        "endpoint": "GET /api/v1/supplier/orders",
        "period_attestation": {
            **period.as_dict(),
            "covered_start": covered_start,
            "covered_end": covered_end,
            "row_count": len(rows),
            "exact_window_confirmed": (
                covered_start == period.start.isoformat()
                and covered_end == period.end.isoformat()
            ),
        },
    }


class OwnerBotStrictSingleNmidReadOnlyPlane:
    """Job-runtime plane: shared Owner-bot evidence loader без duplicate HTTP."""

    def __init__(self) -> None:
        self._cache: dict[tuple[str, int, str, str], OwnerBotEvidenceBundle] = {}
        self._runtime = JobScopedEvidenceRuntime()
        self._load_failure: EvidenceReaderFailure | None = None

    @property
    def _loop(self) -> Any:
        """Совместимость с существующими unit tests."""
        return self._runtime.loop

    def _run_coroutine(self, coro: Any) -> Any:
        return self._runtime.run(coro)

    def close(self) -> None:
        """Закрыть Job-scoped runtime после bounded run."""
        self._runtime.close()

    def ensure_bundle(self, identity: AuditIdentity, period: AuditPeriod) -> None:
        """Предзагрузить bundle до sync section readers (один async load)."""
        self._bundle(identity, period)

    def _bundle(self, identity: AuditIdentity, period: AuditPeriod) -> OwnerBotEvidenceBundle:
        if self._load_failure is not None:
            raise self._load_failure
        key = (
            identity.shop_id,
            identity.cabinet,
            period.start.isoformat(),
            period.end.isoformat(),
        )
        if key in self._cache:
            return self._cache[key]

        try:
            bundle = self._runtime.run(
                load_owner_bot_evidence_bundle(
                    identity.shop_id,
                    identity.cabinet,
                    period.start,
                    period.end,
                    runtime=self._runtime,
                )
            )
        except EvidenceReaderFailure as exc:
            self._load_failure = exc
            raise
        self._cache[key] = bundle
        return bundle

    def read_current_contour(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Прочитать current contour из PG/WB без A1 fallback."""
        bundle = self._bundle(identity, period)
        rows = [
            row
            for row in bundle.pg_rows
            if identity.nmid in _parse_nmids(row.get("nmids"))
        ]
        if not rows:
            yield evidence(
                identity,
                "current_contour",
                "nmid_offer",
                None,
                source="owner-bot-pg-advsetting",
                provenance={"reason": "no advsetting row for exact nmid"},
                period=period,
                present=False,
            )
            return
        row = rows[0]
        mapping: list[tuple[str, Any]] = [
            ("nmid_offer", {"nmid": identity.nmid, "size_id": identity.size_id}),
            ("adv_setting", {"adv_id": _read_int(row, "adv_id") or None}),
            (
                "auto",
                {"adv_id": _read_int(row, "adv_id") or None, "type": row.get("type")},
            ),
            (
                "search",
                {"search_adv_id": _read_int(row, "_search_adv_id") or None},
            ),
            (
                "other_ids",
                {
                    "adv_id": _read_int(row, "adv_id") or None,
                    "search_adv_id": _read_int(row, "_search_adv_id") or None,
                },
            ),
            ("wb_statuses", {"active_status": row.get("active_status")}),
            ("bot_settings", {"bot_active": row.get("bot_active")}),
            (
                "cpo",
                {
                    "target_price_for_order": row.get("target_price_for_order"),
                    "max_price_for_order": row.get("max_price_for_order"),
                },
            ),
            (
                "limits",
                {
                    "auto_budget_daily_limit": row.get("auto_budget_daily_limit"),
                    "search_auto_budget_daily_limit": row.get(
                        "search_auto_budget_daily_limit"
                    ),
                    "common_budget_daily_limit": row.get("common_budget_daily_limit"),
                },
            ),
        ]
        for field_name, value in mapping:
            yield evidence(
                identity,
                "current_contour",
                field_name,
                value,
                source="owner-bot-pg-advsetting",
                provenance={"source": "public.advsetting", "read_only": True},
                period=period,
            )

    def read_orders(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Orders/units/GMV через ORDERS_OR_SALES_REPORTS_READ identity."""
        bundle = self._bundle(identity, period)
        scoped = [
            row
            for row in bundle.orders
            if _read_int(row, "nmId", "nmID", "nm_id") == identity.nmid
            and (day := _row_day(row)) is not None
            and period.start <= day <= period.end
            and not _is_cancel(row)
        ]
        attestation = _orders_attestation(period, scoped)
        orders_count = len(scoped)
        units = sum(_read_int(row, "quantity", "qty") or 1 for row in scoped)
        gmv = sum(_read_number(row, "finishedPrice", "priceWithDisc") or 0.0 for row in scoped)
        for field_name, value in (
            ("orders", orders_count),
            ("units", units),
            ("gmv", round(gmv, 2)),
        ):
            yield evidence(
                identity,
                "orders",
                field_name,
                value,
                source="statistics-reports",
                provenance=attestation,
                period=period,
            )

    def read_attribution(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Direct/associated counts только при explicit fullstats membership."""
        bundle = self._bundle(identity, period)
        direct = associated = 0
        for item in bundle.fullstats:
            adv_id = _read_int(item, "advertId", "advert_id", "id")
            if not adv_id:
                continue
            membership = bundle.memberships.get(adv_id, set())
            if not membership:
                continue
            days = item.get("days")
            if not isinstance(days, list):
                continue
            for day in days:
                if not isinstance(day, dict):
                    continue
                parsed = _parse_day(day.get("date"))
                if parsed is None or not period.start <= parsed <= period.end:
                    continue
                apps = day.get("apps")
                if not isinstance(apps, list):
                    continue
                for app in apps:
                    nms = app.get("nms") if isinstance(app, dict) else None
                    if not isinstance(nms, list):
                        continue
                    for nm in nms:
                        if not isinstance(nm, dict):
                            continue
                        ordered = _read_int(nm, "nmId", "nmID", "nm_id", "id")
                        if ordered != identity.nmid:
                            continue
                        orders = _read_int(nm, "orders")
                        if ordered in membership:
                            direct += orders
                        else:
                            associated += orders
        if direct == 0 and associated == 0:
            yield evidence(
                identity,
                "attribution",
                "direct",
                None,
                source="owner-bot-promotion-fullstats",
                provenance={"reason": "no authoritative attribution rows"},
                period=period,
                complete=False,
                attribution_class="direct",
            )
            yield evidence(
                identity,
                "attribution",
                "associated",
                None,
                source="owner-bot-promotion-fullstats",
                provenance={"reason": "no authoritative attribution rows"},
                period=period,
                complete=False,
                attribution_class="associated",
            )
            return
        yield evidence(
            identity,
            "attribution",
            "direct",
            direct,
            source="owner-bot-promotion-fullstats",
            provenance={"membership": "explicit"},
            period=period,
            attribution_class="direct",
        )
        yield evidence(
            identity,
            "attribution",
            "associated",
            associated,
            source="owner-bot-promotion-fullstats",
            provenance={"membership": "explicit"},
            period=period,
            attribution_class="associated",
        )

    def read_topology(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Topology только при explicit campaign membership для nmid."""
        bundle = self._bundle(identity, period)
        memberships = {
            adv_id: sorted(nmids)
            for adv_id, nmids in bundle.memberships.items()
            if identity.nmid in nmids
        }
        if not memberships:
            yield evidence(
                identity,
                "topology",
                "topology",
                None,
                source="owner-bot-membership",
                provenance={"reason": "authoritative topology not evidenced"},
                period=period,
                complete=False,
            )
            return
        yield evidence(
            identity,
            "topology",
            "topology",
            memberships,
            source="owner-bot-membership",
            provenance={"membership_map": memberships},
            period=period,
        )

    def read_stock(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[Evidence]:
        """Stock views без unsupported inference — explicit unsupported."""
        del identity, period
        return []

    def read_physical_spend(
        self, identity: AuditIdentity, period: AuditPeriod
    ) -> Iterable[SpendEvidence]:
        """Physical spend из promotion fullstats campaign-day rows."""
        bundle = self._bundle(identity, period)
        total = Decimal("0")
        overlap_keys: set[str] = set()
        for item in bundle.fullstats:
            adv_id = _read_int(item, "advertId", "advert_id", "id")
            if not adv_id or identity.nmid not in bundle.memberships.get(adv_id, set()):
                continue
            days = item.get("days")
            if not isinstance(days, list):
                continue
            for day in days:
                if not isinstance(day, dict):
                    continue
                parsed = _parse_day(day.get("date"))
                if parsed is None or not period.start <= parsed <= period.end:
                    continue
                spend = _read_number(day, "sum", "spend") or 0.0
                if spend <= 0:
                    continue
                overlap_key = f"physical:{adv_id}:{parsed.isoformat()}"
                if overlap_key in overlap_keys:
                    continue
                overlap_keys.add(overlap_key)
                total += Decimal(str(spend))
        if total <= 0:
            yield SpendEvidence(
                amount=None,
                source="owner-bot-promotion-fullstats",
                overlap_key=None,
                identity=identity,
                period=period,
                provenance={"reason": "no physical spend in window"},
                status=GAP,
            )
            return
        yield SpendEvidence(
            amount=total,
            source="owner-bot-promotion-fullstats",
            overlap_key="physical:canonical",
            identity=identity,
            period=period,
            provenance={"overlap_keys": sorted(overlap_keys)},
            status=CONFIRMED,
        )


def build_owner_bot_read_only_plane() -> OwnerBotStrictSingleNmidReadOnlyPlane:
    """Создать Job-runtime plane без side effects."""
    return OwnerBotStrictSingleNmidReadOnlyPlane()
