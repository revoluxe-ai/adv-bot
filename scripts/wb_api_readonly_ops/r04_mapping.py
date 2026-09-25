"""Mapping gate COL-R04-001: GET_OR_DOCUMENTED_POST_AS_READ.

Mandatory families: ORDERS / STATISTICS / CAMPAIGNS.
CONTENT_CARDS optional with disclosed gap.
Does not invent live HTTP accessibility; mapping ≠ accessibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from scripts.wb_api_readonly_ops.r04_constants import (
    FAMILY_CAMPAIGNS,
    FAMILY_CARDS,
    FAMILY_ORDERS,
    FAMILY_STATISTICS,
    MANDATORY_FAMILIES,
    READ_ONLY_METHOD_POLICY,
)


def _str_list() -> list[str]:
    """Typed default_factory list[str]."""
    return []


@dataclass(frozen=True)
class R04FamilyMapping:
    """Результат mapping/allowlist для одной r04 family."""

    family: str
    disposition: str  # PASS_MAP | REFUSED | OPTIONAL_DISCLOSED_GAP
    method_class: str  # GET_READ | POST_DOCUMENTED_AS_READ | …
    method: str
    path_or_note: str
    mandatory: bool
    doc_binding: str
    blockers: tuple[str, ...] = ()
    evidence_note: str = ""


def _families() -> list[R04FamilyMapping]:
    """Typed default_factory."""
    return []


@dataclass
class R04MappingGateResult:
    """Итог r04 family gate + blockers."""

    families: list[R04FamilyMapping] = field(default_factory=_families)
    method_policy: str = READ_ONLY_METHOD_POLICY
    api_preflight: str = "REFUSED"  # PASS | REFUSED
    blockers: list[str] = field(default_factory=_str_list)

    @property
    def mandatory_pass_count(self) -> int:
        """Сколько mandatory families с PASS_MAP."""
        return sum(
            1
            for f in self.families
            if f.mandatory and f.disposition == "PASS_MAP"
        )


def build_r04_mapping_gate(
    *,
    campaigns_live_ok: bool | None = None,
) -> R04MappingGateResult:
    """Собрать honest r04 mapping из локального стека (без invent URL).

    Args:
        campaigns_live_ok: None → PASS_MAP по adapter; False → REFUSED;
            True → PASS_MAP после live probe (attested by Job, not Cursor).

    Returns:
        R04MappingGateResult. api_preflight=PASS только если все
        mandatory PASS_MAP (CONTENT optional).
    """
    if campaigns_live_ok is False:
        campaigns = R04FamilyMapping(
            family=FAMILY_CAMPAIGNS,
            disposition="REFUSED",
            method_class="GET_READ",
            method="GET",
            path_or_note="/adv/v1/promotion/count",
            mandatory=True,
            doc_binding=(
                "local_adapter:promotion_client/promotion_count"
                "|WB_ADV_PROMOTION_COUNT"
            ),
            blockers=("LIVE_CAMPAIGNS_PROBE_FAILED",),
            evidence_note="Existing promotion_count adapter; live probe failed",
        )
    else:
        campaigns = R04FamilyMapping(
            family=FAMILY_CAMPAIGNS,
            disposition="PASS_MAP",
            method_class="GET_READ",
            method="GET",
            path_or_note="/adv/v1/promotion/count",
            mandatory=True,
            doc_binding=(
                "local_adapter:app/core/mp/wb/api/adapter/"
                "promotion_client/promotion_count→get_cabinet_adv_ids"
            ),
            blockers=(),
            evidence_note="Local GET adapter mapped; HTTP accessibility not asserted here",
        )

    orders = R04FamilyMapping(
        family=FAMILY_ORDERS,
        disposition="REFUSED",
        method_class="GET_READ",
        method="GET",
        path_or_note="statistics-api supplier orders/sales (reports)",
        mandatory=True,
        doc_binding="UNRESOLVED_OWNER_LOCAL_GET_MAPPING",
        blockers=(
            "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
            "PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY",
        ),
        evidence_note=(
            "L0 ORDERS family exists for research; r04 contemporaneous "
            "PASS_MAP for required dataset not claimed in packager path"
        ),
    )
    statistics = R04FamilyMapping(
        family=FAMILY_STATISTICS,
        disposition="REFUSED",
        method_class="GET_READ",
        method="GET",
        path_or_note="/adv/v3/fullstats",
        mandatory=True,
        doc_binding="UNRESOLVED_OWNER_LOCAL_GET_MAPPING",
        blockers=(
            "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET",
            "READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED",
            "PREBOUND_ADVERT_ID_REQUIRED",
        ),
        evidence_note="fullstats needs pre-bound advertId; not Stage A PASS_MAP",
    )
    cards = R04FamilyMapping(
        family=FAMILY_CARDS,
        disposition="OPTIONAL_DISCLOSED_GAP",
        method_class="POST_DOCUMENTED_AS_READ",
        method="POST",
        path_or_note="/content/v2/get/cards/list",
        mandatory=False,
        doc_binding=(
            "WB_CONTENT_API_cards_list_POST|"
            "classified_POST_DOCUMENTED_AS_READ_under_r04_policy|"
            "allowlist_pending_Owner_local_immutable_hash"
        ),
        blockers=("CONTENT_CARDS_OPTIONAL_DISCLOSED_GAP",),
        evidence_note=(
            "r04 allows POST_DOCUMENTED_AS_READ; family optional with "
            "disclosed gap until Owner-local immutable doc hash + allowlist entry"
        ),
    )

    families = [orders, statistics, campaigns, cards]
    blockers: list[str] = []
    for item in families:
        if item.mandatory and item.disposition != "PASS_MAP":
            blockers.extend(item.blockers)

    mandatory_ok = all(
        f.disposition == "PASS_MAP"
        for f in families
        if f.family in MANDATORY_FAMILIES
    )
    api_preflight = "PASS" if mandatory_ok else "REFUSED"

    seen: set[str] = set()
    uniq: list[str] = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            uniq.append(b)

    return R04MappingGateResult(
        families=families,
        method_policy=READ_ONLY_METHOD_POLICY,
        api_preflight=api_preflight,
        blockers=uniq,
    )
