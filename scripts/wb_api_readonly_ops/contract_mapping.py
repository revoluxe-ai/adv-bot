"""Локальный mapping gate COL-R03-009 без invent URL.

Spec: Honest REFUSED still packages RETURN.
Campaigns: PASS_MAP через existing GET /adv/v1/promotion/count adapter.
ORDERS / STATISTICS / CARDS: honest REFUSED с exact blockers (inventory).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.wb_api_readonly_ops.contract_constants import (
    ALIAS_CAMPAIGNS,
    ALIAS_CARDS,
    ALIAS_ORDERS,
    ALIAS_STATISTICS,
)


def _blockers() -> list[str]:
    """Typed default_factory для list[str]."""
    return []


@dataclass(frozen=True)
class AliasMapping:
    """Результат mapping gate для одного required alias."""

    alias: str
    disposition: str  # PASS_MAP | REFUSED
    method: str
    path_or_note: str
    blockers: tuple[str, ...] = ()
    evidence_note: str = ""


def _aliases() -> list[AliasMapping]:
    """Typed default_factory для list[AliasMapping]."""
    return []


@dataclass
class MappingGateResult:
    """Итог четырёх required aliases + blockers для 00_STATUS."""

    aliases: list[AliasMapping] = field(default_factory=_aliases)
    api_preflight: str = "REFUSED"  # PASS_CANDIDATE | REFUSED
    blockers: list[str] = field(default_factory=_blockers)

    @property
    def pass_map_count(self) -> int:
        """Сколько aliases с PASS_MAP."""
        return sum(1 for a in self.aliases if a.disposition == "PASS_MAP")


def build_default_mapping_gate(
    *,
    campaigns_live_ok: bool | None = None,
) -> MappingGateResult:
    """Собрать honest mapping из локального стека (без invent URL).

    Args:
        campaigns_live_ok: None → PASS_MAP по наличию adapter (без live);
            True → PASS_MAP после live probe; False → REFUSED для campaigns.

    Returns:
        MappingGateResult с api_preflight REFUSED пока не все 4 PASS_MAP
        (COL-R03-009 pass-candidate rule требует все aliases).
    """
    if campaigns_live_ok is False:
        campaigns = AliasMapping(
            alias=ALIAS_CAMPAIGNS,
            disposition="REFUSED",
            method="GET",
            path_or_note="/adv/v1/promotion/count",
            blockers=("LIVE_CAMPAIGNS_PROBE_FAILED",),
            evidence_note="Existing promotion_count adapter; live probe failed",
        )
    else:
        campaigns = AliasMapping(
            alias=ALIAS_CAMPAIGNS,
            disposition="PASS_MAP",
            method="GET",
            path_or_note="/adv/v1/promotion/count",
            blockers=(),
            evidence_note=(
                "Local adapter "
                "app/core/mp/wb/api/adapter/promotion_client/"
                "promotion_count → get_cabinet_adv_ids"
            ),
        )

    orders = AliasMapping(
        alias=ALIAS_ORDERS,
        disposition="REFUSED",
        method="GET",
        path_or_note="statistics-api supplier orders/sales (reports)",
        blockers=(
            "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
            "TARGET_PERIOD_NOT_APPLIED_FOR_PROMOTION_STATISTICS",
        ),
        evidence_note=(
            "L0 ORDERS family exists for research collect; COL-R03-009 "
            "contemporaneous GET attestation for required dataset not claimed "
            "as PASS_MAP in this packager path"
        ),
    )
    statistics = AliasMapping(
        alias=ALIAS_STATISTICS,
        disposition="REFUSED",
        method="GET",
        path_or_note="/adv/v3/fullstats",
        blockers=(
            "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
            "READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED",
        ),
        evidence_note="fullstats needs pre-bound advertId; not Stage A PASS_MAP",
    )
    cards = AliasMapping(
        alias=ALIAS_CARDS,
        disposition="REFUSED",
        method="POST",
        path_or_note="/content/v2/get/cards/list",
        blockers=("NO_GET_ONLY_ENDPOINT_FOR_REQUIRED_DATASET",),
        evidence_note="cards list is POST-read; COL-R03-009 requires GET-only",
    )

    aliases = [orders, statistics, campaigns, cards]
    blockers: list[str] = []
    for item in aliases:
        if item.disposition == "REFUSED":
            blockers.extend(item.blockers)

    # Pass-candidate только если все 4 PASS_MAP (контракт §8).
    api_preflight = (
        "PASS_CANDIDATE"
        if all(a.disposition == "PASS_MAP" for a in aliases)
        else "REFUSED"
    )
    # Deduplicate blockers preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            uniq.append(b)

    return MappingGateResult(
        aliases=aliases,
        api_preflight=api_preflight,
        blockers=uniq,
    )
