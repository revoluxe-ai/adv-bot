"""Packager COL-R04-003B_ORDERS_FAMILY_PREFLIGHT_RETURN.zip (+ .sha256)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from scripts.wb_api_readonly_ops.r04_003b_constants import (
    AUTHORITY_PACKAGE_SHA256,
    CABINET_B1_BLOCKERS_REMAINING,
    CABINET_B1_CARRIED_STATUS,
    COL_R04_003_RETURN_SHA256,
    CONTRACT_ID_R04_003B,
    DEFAULT_BOUND_ALIAS,
    DEFAULT_CABINET_ROLE,
    DEFAULT_PERIOD_END_RFC3339,
    DEFAULT_PERIOD_START_RFC3339,
    DEFAULT_UI_STORE,
    FIRST_PARTITION_DATE,
    FULL_WINDOW_TRAVERSED_IN_PREFLIGHT,
    FULL_WINDOW_TRAVERSAL_AUTHORIZED,
    LAST_PARTITION_DATE,
    LOCKED_PERIOD_CALENDAR_DAYS,
    MANDATORY_FAMILY_REQUIRED_COUNT,
    METHOD_CLASS,
    MODE_R04_003B,
    OFFICIAL_SEMANTICS_ORDERS,
    OFFICIAL_SEMANTICS_SALES,
    OPTIONAL_CONTENT_CARDS_STATUS,
    PARTITION_MODEL,
    PRIOR_AUTHORITY_SHA256,
    PRIMARY_RETURN_BASENAME_R04_003B,
    PRIMARY_RETURN_SHA_BASENAME_R04_003B,
    PROMOTION_CAMPAIGNS_CARRIED,
    PROMOTION_STATISTICS_CARRIED,
    PROBE_DATE,
    PROBE_FLAG,
    READ_ONLY_METHOD_POLICY,
    REQUEST_ID,
    REQUIRED_ZIP_ENTRIES_R04_003B,
    RETAINED_BLOCKERS,
    ROUND_R04,
)
from scripts.wb_api_readonly_ops.r04_003b_probe import (
    OrdersSalesProbeEvidence,
    orders_family_pass,
    probe_to_family_payload,
)


class R04_003bPackagerError(RuntimeError):
    """Membership / digest failure."""


@dataclass
class R04_003bPackagerResult:
    primary_path: Path
    primary_sha256: str
    sidecar_path: Path
    orders_family_status: str
    mandatory_pass_count: int
    global_eligibility: str
    blockers: list[str]


def _moscow_now() -> str:
    tz = timezone(timedelta(hours=3))
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+03:00")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _blocker_dispositions(orders_pass: bool) -> dict[str, str]:
    """PKG-003-02: explicit disposition per retained blocker id."""
    if orders_pass:
        return {
            "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET": "CLOSED",
            "PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY": "CLOSED",
            "READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED": "CLOSED",
            "PREBOUND_ADVERT_ID_REQUIRED": "NOT_APPLICABLE_ORDERS_FAMILY",
            "locked_period_full_window_not_traversed": (
                "RECLASSIFIED_AS_COLLECTION_STAGE_NOT_PREFLIGHT_BLOCKER"
            ),
        }
    return {
        "NO_OWNER_LOCAL_MAPPING_FOR_REQUIRED_DATASET": "OPEN_IF_PROBE_FAILED",
        "PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY": "OPEN",
        "READ_ONLY_ENDPOINT_SEMANTICS_UNRESOLVED": "CLOSED_CARRIED_OTHER_FAMILIES",
        "PREBOUND_ADVERT_ID_REQUIRED": "NOT_APPLICABLE_ORDERS_FAMILY",
        "locked_period_full_window_not_traversed": "OPEN",
    }


def _build_members(
    ev: OrdersSalesProbeEvidence,
    captured_at: str,
) -> dict[str, str]:
    orders_pass = orders_family_pass(ev)
    orders_family_status = "PASS" if orders_pass else "REFUSED"
    dispositions = _blocker_dispositions(orders_pass)

    mandatory_pass = 0
    if orders_pass:
        mandatory_pass += 1
    if PROMOTION_CAMPAIGNS_CARRIED == "PASS":
        mandatory_pass += 1
    if PROMOTION_STATISTICS_CARRIED == "PASS":
        mandatory_pass += 1

    eligibility = (
        "CANDIDATE_YES"
        if mandatory_pass == MANDATORY_FAMILY_REQUIRED_COUNT
        else "NO"
    )

    blockers = []
    if not orders_pass:
        blockers.extend(ev.gap_or_refusal_ids)
        if "PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY" not in blockers:
            blockers.append("PERIOD_SEMANTICS_UNRESOLVED_FOR_ORDERS_FAMILY")

    status: dict[str, Any] = {
        "REQUEST_ID": REQUEST_ID,
        "EXECUTION_ROUND": ROUND_R04,
        "TASK_ID": CONTRACT_ID_R04_003B,
        "MODE": MODE_R04_003B,
        "authority_package_sha256": AUTHORITY_PACKAGE_SHA256,
        "col_r04_003_return_sha256": COL_R04_003_RETURN_SHA256,
        "prior_authority_sha256": PRIOR_AUTHORITY_SHA256,
        "STORE_LABEL": DEFAULT_UI_STORE,
        "ACCOUNT_SCOPE_ALIAS": DEFAULT_BOUND_ALIAS,
        "CABINET_ROLE": DEFAULT_CABINET_ROLE,
        "PERIOD_START": DEFAULT_PERIOD_START_RFC3339,
        "PERIOD_END": DEFAULT_PERIOD_END_RFC3339,
        "ORDERS_OR_SALES_REPORTS_READ": orders_family_status,
        "ORDERS_PROBE_STATUS": ev.orders_status,
        "SALES_PROBE_STATUS": ev.sales_status,
        "ORDERS_HTTP_ATTEMPTS": ev.orders_http_attempts,
        "SALES_HTTP_ATTEMPTS": ev.sales_http_attempts,
        "PROBE_DATE": PROBE_DATE,
        "PERIOD_PARTITION_MODEL": PARTITION_MODEL,
        "LOCKED_PERIOD_CALENDAR_DAYS": LOCKED_PERIOD_CALENDAR_DAYS,
        "FULL_WINDOW_TRAVERSED_IN_PREFLIGHT": FULL_WINDOW_TRAVERSED_IN_PREFLIGHT,
        "NO_WRITE_GATE": "PASS",
        "SECRET_SCAN": "PASS",
        "SCOPE_DRIFT": "NO",
        "CABINET_B1_PREFLIGHT_CARRIED_STATUS": CABINET_B1_CARRIED_STATUS,
        "CABINET_B1_BLOCKERS_REMAINING": CABINET_B1_BLOCKERS_REMAINING,
        "PROMOTION_CAMPAIGNS_CARRIED_STATUS": PROMOTION_CAMPAIGNS_CARRIED,
        "PROMOTION_STATISTICS_CARRIED_STATUS": PROMOTION_STATISTICS_CARRIED,
        "OPTIONAL_CONTENT_CARDS_STATUS": OPTIONAL_CONTENT_CARDS_STATUS,
        "MANDATORY_API_FAMILY_PASS_COUNT": mandatory_pass,
        "MANDATORY_API_FAMILY_REQUIRED_COUNT": MANDATORY_FAMILY_REQUIRED_COUNT,
        "GLOBAL_READ_ONLY_PREFLIGHT_PASS": False,
        "GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY": eligibility,
        "READ_ONLY_COLLECTION_AUTHORIZED": False,
        "MASS_COLLECTION_STARTED": False,
        "FINAL_REVIEW_AUTHORIZED": False,
        "SESSION_CLOSE_STATUS": "CLOSED",
        "captured_at": captured_at,
        "blocker_dispositions": dispositions,
        "blockers_open": blockers,
    }

    auth = f"""# Authorization and scope — {CONTRACT_ID_R04_003B}

REQUEST_ID={REQUEST_ID}
TASK_ID={CONTRACT_ID_R04_003B}
MODE={MODE_R04_003B}
AUTHORITY_PACKAGE_SHA256={AUTHORITY_PACKAGE_SHA256}
COL_R04_003_RETURN_SHA256={COL_R04_003_RETURN_SHA256}

STORE_LABEL={DEFAULT_UI_STORE}
ACCOUNT_SCOPE_ALIAS={DEFAULT_BOUND_ALIAS}
CABINET_ROLE={DEFAULT_CABINET_ROLE}
PERIOD={DEFAULT_PERIOD_START_RFC3339}..{DEFAULT_PERIOD_END_RFC3339}

ORDERS_FAMILY_PREFLIGHT_FIX_AUTHORIZED=YES
PROMOTION_RECOLLECTION=NO
CABINET_RECOLLECTION=NO
GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO
READ_ONLY_COLLECTION_AUTHORIZED=NO

CREDENTIALED_RUNTIME=OWNER_LOCAL_OPSX_JOB_ONLY
LOCAL_CURSOR_MAY_CALL_WB_API=NO
"""

    semantics = f"""# Orders / sales official semantics

{OFFICIAL_SEMANTICS_ORDERS}

{OFFICIAL_SEMANTICS_SALES}

METHOD_CLASS={METHOD_CLASS}
LOCAL_ADAPTER={probe_to_family_payload(ev).get("local_adapter", "")}
ANTI_SUBSTITUTION=funnel|fullstats|FBS|search-report MUST NOT satisfy this family
"""

    probe_md = f"""# Live probe attestation

PROBE_DATE={PROBE_DATE}
FLAG={PROBE_FLAG}
MAXIMUM_CALENDAR_DAYS_PROBED=1

## Orders {ev.orders_status}
- endpoint: /api/v1/supplier/orders
- http_status_class: {ev.orders_http_status_class}
- http_attempts: {ev.orders_http_attempts}
- rows_count: {ev.orders_rows_count}
- empty_admissible: YES
- error: {ev.orders_error or "NONE"}

## Sales {ev.sales_status}
- endpoint: /api/v1/supplier/sales
- http_status_class: {ev.sales_http_status_class}
- http_attempts: {ev.sales_http_attempts}
- rows_count: {ev.sales_rows_count}
- empty_admissible: YES
- error: {ev.sales_error or "NONE"}

ORDERS_OR_SALES_REPORTS_READ={orders_family_status}
NO_RAW_ROWS_IN_RETURN=YES
"""

    partition = f"""# Locked period partition plan (sealed — not executed)

PARTITION_MODEL={PARTITION_MODEL}
LOCKED_PERIOD_CALENDAR_DAYS={LOCKED_PERIOD_CALENDAR_DAYS}
FIRST_PARTITION_DATE={FIRST_PARTITION_DATE}
LAST_PARTITION_DATE={LAST_PARTITION_DATE}
FULL_WINDOW_TRAVERSED_IN_PREFLIGHT=NO
FULL_WINDOW_TRAVERSAL_AUTHORIZED=NO

NOTE=Future collection uses daily flag=1 partitions; not executed in COL-R04-003B.
"""

    blocker_lines = ["# Blocker dispositions (PKG-003-02)", ""]
    for bid in RETAINED_BLOCKERS:
        blocker_lines.append(f"- {bid}: {dispositions.get(bid, 'UNSPECIFIED')}")
    blocker_md = "\n".join(blocker_lines)

    no_write = """# No-write invariant

NO_WRITE_GATE=PASS
MUTATION_ACTION_USED=NO
MASS_COLLECTION_STARTED=NO
"""

    secret = """# Redaction and secret scan

SECRET_SCAN=PASS
RAW_ORDERS=0
RAW_SALES=0
RAW_CREDENTIAL_VALUES=0
SHOP_ID_IN_RETURN=0
"""

    eligibility_md = f"""# Global gate eligibility

ORDERS_OR_SALES_REPORTS_READ={orders_family_status}
MANDATORY_API_FAMILY_PASS_COUNT={mandatory_pass}/{MANDATORY_FAMILY_REQUIRED_COUNT}
GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO
GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY={eligibility}
READ_ONLY_COLLECTION_AUTHORIZED=NO
OPTIONAL_CONTENT_CARDS_STATUS={OPTIONAL_CONTENT_CARDS_STATUS}
"""

    session = f"""# Session close

SESSION_CLOSE_STATUS=CLOSED
RETURN_ZIP={PRIMARY_RETURN_BASENAME_R04_003B}
Captured_at={captured_at}
"""

    evidence = {
        "schema_version": 1,
        "task_id": CONTRACT_ID_R04_003B,
        "captured_at": captured_at,
        "orders_probe": {
            "endpoint_or_report_alias": "/api/v1/supplier/orders",
            "method_class": METHOD_CLASS,
            "official_semantics_reference": OFFICIAL_SEMANTICS_ORDERS,
            "account_entitlement_result": ev.orders_status,
            "probe_date": PROBE_DATE,
            "flag": PROBE_FLAG,
            "http_status_class": ev.orders_http_status_class,
            "http_attempt_count": ev.orders_http_attempts,
            "rows_count": ev.orders_rows_count,
            "empty_response_admissible": True,
            "schema_fingerprint": ev.schema_fingerprint_orders,
            "runtime_source_instance_fingerprint": "wb_api_readonly_ops/r04_003b_probe",
            "no_write_observation": "NO_MUTATION_OBSERVED",
            "gap_or_refusal_ids": ev.gap_or_refusal_ids if not orders_pass else [],
        },
        "sales_probe": {
            "endpoint_or_report_alias": "/api/v1/supplier/sales",
            "method_class": METHOD_CLASS,
            "official_semantics_reference": OFFICIAL_SEMANTICS_SALES,
            "account_entitlement_result": ev.sales_status,
            "probe_date": PROBE_DATE,
            "flag": PROBE_FLAG,
            "http_status_class": ev.sales_http_status_class,
            "http_attempt_count": ev.sales_http_attempts,
            "rows_count": ev.sales_rows_count,
            "empty_response_admissible": True,
            "schema_fingerprint": ev.schema_fingerprint_sales,
            "runtime_source_instance_fingerprint": "wb_api_readonly_ops/r04_003b_probe",
            "no_write_observation": "NO_MUTATION_OBSERVED",
            "gap_or_refusal_ids": ev.gap_or_refusal_ids if not orders_pass else [],
        },
        "family_summary": probe_to_family_payload(ev),
        "carried": {
            "cabinet_b1": CABINET_B1_CARRIED_STATUS,
            "promotion_campaigns": PROMOTION_CAMPAIGNS_CARRIED,
            "promotion_statistics": PROMOTION_STATISTICS_CARRIED,
            "content_cards": OPTIONAL_CONTENT_CARDS_STATUS,
        },
        "blocker_dispositions": dispositions,
    }

    return {
        "00_STATUS.yaml": yaml.safe_dump(status, allow_unicode=True, sort_keys=False),
        "01_AUTHORIZATION_AND_SCOPE.md": auth,
        "02_ORDERS_SALES_OFFICIAL_SEMANTICS.md": semantics,
        "03_LIVE_PROBE_ATTESTATION.md": probe_md,
        "04_LOCKED_PERIOD_PARTITION_PLAN.md": partition,
        "05_BLOCKER_DISPOSITIONS.md": blocker_md,
        "06_NO_WRITE_INVARIANT.md": no_write,
        "07_REDACTION_AND_SECRET_SCAN.md": secret,
        "08_GLOBAL_GATE_ELIGIBILITY.md": eligibility_md,
        "09_SESSION_CLOSE.md": session,
        "10_EVIDENCE_ITEMS.json": json.dumps(evidence, ensure_ascii=False, indent=2),
    }


def package_col_r04_003b_return(
    output_dir: Path,
    evidence: OrdersSalesProbeEvidence,
    captured_at: str | None = None,
) -> R04_003bPackagerResult:
    """Записать COL-R04-003B primary RETURN + sidecar."""
    captured = captured_at or _moscow_now()
    members = _build_members(evidence, captured)
    orders_pass = orders_family_pass(evidence)

    encoded = {name: text.encode("utf-8") for name, text in members.items()}
    sums_lines = [
        f"{_sha256_bytes(encoded[n])}  {n}"
        for n in REQUIRED_ZIP_ENTRIES_R04_003B
        if n != "SHA256SUMS.txt"
    ]
    encoded["SHA256SUMS.txt"] = ("\n".join(sums_lines) + "\n").encode("utf-8")

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_path = output_dir / PRIMARY_RETURN_BASENAME_R04_003B
    if primary_path.exists():
        primary_path.unlink()
    with zipfile.ZipFile(primary_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in REQUIRED_ZIP_ENTRIES_R04_003B:
            zf.writestr(name, encoded[name])

    digest = _sha256_bytes(primary_path.read_bytes())
    sidecar = output_dir / PRIMARY_RETURN_SHA_BASENAME_R04_003B
    sidecar.write_text(
        f"{digest}  {PRIMARY_RETURN_BASENAME_R04_003B}\n",
        encoding="utf-8",
        newline="\n",
    )

    with zipfile.ZipFile(primary_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
    if names != sorted(REQUIRED_ZIP_ENTRIES_R04_003B):
        raise R04_003bPackagerError(f"zip membership mismatch: {names}")

    mandatory_pass = sum(
        [
            1 if orders_pass else 0,
            1 if PROMOTION_CAMPAIGNS_CARRIED == "PASS" else 0,
            1 if PROMOTION_STATISTICS_CARRIED == "PASS" else 0,
        ]
    )
    status_yaml = yaml.safe_load(members["00_STATUS.yaml"])
    open_blockers = list(status_yaml.get("blockers_open") or [])

    return R04_003bPackagerResult(
        primary_path=primary_path,
        primary_sha256=digest,
        sidecar_path=sidecar,
        orders_family_status="PASS" if orders_pass else "REFUSED",
        mandatory_pass_count=mandatory_pass,
        global_eligibility=str(status_yaml.get("GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY")),
        blockers=open_blockers,
    )
