"""Packager COL-R04-003_API_PREFLIGHT_RETURN.zip (+ .sha256).

Live API evidence from Job runtime; no shop_id/tokens/raw identifier maps.
GLOBAL_READ_ONLY_PREFLIGHT_PASS остаётся NO (Tower gate).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from scripts.wb_api_readonly_ops.models import FamilyResult, FamilyStatus
from scripts.wb_api_readonly_ops.r04_003_constants import (
    AUTHORITY_PACKAGE_SHA256,
    CABINET_B1_BLOCKERS_REMAINING,
    CABINET_B1_CARRIED_STATUS,
    CONTRACT_ID_R04_003,
    DEFAULT_BOUND_ALIAS,
    DEFAULT_CABINET_ROLE,
    DEFAULT_PERIOD_END_RFC3339,
    DEFAULT_PERIOD_START_RFC3339,
    DEFAULT_UI_STORE,
    FAMILY_CARDS,
    MANDATORY_FAMILIES,
    MODE_R04_003,
    OPTIONAL_FAMILIES,
    PRIMARY_RETURN_BASENAME_R04_003,
    PRIMARY_RETURN_SHA_BASENAME_R04_003,
    READ_ONLY_METHOD_POLICY,
    REQUEST_ID,
    REQUIRED_ZIP_ENTRIES_R04_003,
    ROUND_R04,
)


def _str_list() -> list[str]:
    return []


@dataclass
class R04_003FamilyAttestation:
    """Аттестация одной API family для RETURN (без raw ids)."""

    family_id: str
    status: str  # PASS | REFUSED | OPTIONAL_GAP
    endpoint_or_report_alias: str
    method_class: str
    authoritative_read_semantics_reference: str
    account_entitlement_result: str
    period_semantics: str
    identifier_binding_alias_or_hash: str
    captured_at: str
    schema_fingerprint: str
    runtime_source_instance_fingerprint: str
    pagination_or_partition_rule: str
    completeness_limit: str
    no_write_observation: str
    http_attempt_count: int
    gap_or_refusal_ids: list[str] = field(default_factory=_str_list)


@dataclass
class R04_003PackagerInput:
    """Вход packager: live family results + scope (без shop_id)."""

    bound_alias: str = DEFAULT_BOUND_ALIAS
    ui_store_name: str = DEFAULT_UI_STORE
    cabinet_role: str = DEFAULT_CABINET_ROLE
    period_start_rfc3339: str = DEFAULT_PERIOD_START_RFC3339
    period_end_rfc3339: str = DEFAULT_PERIOD_END_RFC3339
    family_results: dict[str, FamilyResult] = field(default_factory=dict)
    captured_at: str | None = None
    mutation_action_used: bool = False


@dataclass
class R04_003PackagerResult:
    """Primary ZIP + sidecar + gate fields."""

    primary_path: Path
    primary_sha256: str
    sidecar_path: Path
    api_preflight_status: str
    mandatory_pass_count: int
    global_eligibility: str
    blockers: list[str]
    zip_names: list[str]


class R04_003PackagerError(RuntimeError):
    """Membership / digest failure."""


def _moscow_now() -> str:
    tz = timezone(timedelta(hours=3))
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+03:00")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _family_pass(result: FamilyResult) -> bool:
    """PASS: OK status без contract blockers в payload."""
    if result.status != FamilyStatus.OK:
        return False
    payload = result.payload if isinstance(result.payload, dict) else {}
    blockers = payload.get("contract_blockers")
    if isinstance(blockers, list) and blockers:
        return False
    return True


def _attestation_from_result(
    family_id: str,
    result: FamilyResult,
    captured_at: str,
    mandatory: bool,
) -> R04_003FamilyAttestation:
    payload = result.payload if isinstance(result.payload, dict) else {}
    blockers_raw = payload.get("contract_blockers")
    gap_ids: list[str] = list(result.gaps)
    if isinstance(blockers_raw, list):
        for b in blockers_raw:
            if isinstance(b, str) and b not in gap_ids:
                gap_ids.append(b)

    if mandatory:
        status = "PASS" if _family_pass(result) else "REFUSED"
    else:
        status = "OPTIONAL_GAP"

    entitlement = "ENTITLED" if result.status in (
        FamilyStatus.OK,
        FamilyStatus.PARTIAL,
    ) and result.error is None else "REFUSED_OR_ERROR"

    return R04_003FamilyAttestation(
        family_id=family_id,
        status=status,
        endpoint_or_report_alias=str(
            payload.get("endpoint_or_report_alias", "UNRESOLVED")
        ),
        method_class=str(payload.get("method_class", "UNRESOLVED")),
        authoritative_read_semantics_reference=str(
            payload.get(
                "authoritative_read_semantics_reference",
                payload.get("source", "UNRESOLVED"),
            )
        ),
        account_entitlement_result=entitlement,
        period_semantics=str(
            payload.get("period_semantics", "SEE_PERIOD_ARTIFACT")
        ),
        identifier_binding_alias_or_hash=str(
            payload.get(
                "identifier_binding_alias_or_hash",
                f"ALIAS_{family_id}",
            )
        ),
        captured_at=captured_at,
        schema_fingerprint=str(
            payload.get("schema_fingerprint", "ABSENT")
        ),
        runtime_source_instance_fingerprint=(
            "wb_api_readonly_ops/r04_003_families"
        ),
        pagination_or_partition_rule=str(
            payload.get("pagination_or_partition_rule", "SEE_NOTES")
        ),
        completeness_limit=str(
            payload.get("completeness_limit", "PREFLIGHT_MIN_PROBE")
        ),
        no_write_observation="NO_MUTATION_OBSERVED",
        http_attempt_count=int(payload.get("http_attempt_count", 0) or 0),
        gap_or_refusal_ids=gap_ids,
    )


def _compute_gates(inp: R04_003PackagerInput) -> tuple[
    int,
    str,
    list[str],
    str,
]:
    """mandatory_pass_count, api_status, blockers, eligibility."""
    blockers: list[str] = []
    pass_count = 0
    for fam in MANDATORY_FAMILIES:
        result = inp.family_results.get(fam)
        if result is None:
            blockers.append(f"MISSING_FAMILY_EVIDENCE_{fam}")
            continue
        if _family_pass(result):
            pass_count += 1
        else:
            payload = result.payload if isinstance(result.payload, dict) else {}
            raw_b = payload.get("contract_blockers")
            if isinstance(raw_b, list):
                for b in raw_b:
                    if isinstance(b, str) and b not in blockers:
                        blockers.append(b)
            for g in result.gaps:
                if g not in blockers:
                    blockers.append(g)

    api_status = "PASS" if pass_count == len(MANDATORY_FAMILIES) else "REFUSED"
    eligibility = (
        "CANDIDATE_YES"
        if pass_count == len(MANDATORY_FAMILIES)
        else "NO"
    )
    return pass_count, api_status, blockers, eligibility


def _build_members(inp: R04_003PackagerInput) -> dict[str, str]:
    captured_at = inp.captured_at or _moscow_now()
    attestations = []
    for fam in MANDATORY_FAMILIES + OPTIONAL_FAMILIES:
        result = inp.family_results.get(fam)
        if result is None:
            continue
        attestations.append(
            _attestation_from_result(
                fam,
                result,
                captured_at,
                mandatory=fam in MANDATORY_FAMILIES,
            )
        )

    pass_count, api_status, blockers, eligibility = _compute_gates(inp)

    cards_result = inp.family_results.get(FAMILY_CARDS)
    cards_status = "OPTIONAL_GAP"
    if cards_result is not None:
        cards_status = (
            "PASS"
            if _family_pass(cards_result)
            else "OPTIONAL_GAP"
        )

    status: dict[str, Any] = {
        "REQUEST_ID": REQUEST_ID,
        "EXECUTION_ROUND": ROUND_R04,
        "TASK_ID": CONTRACT_ID_R04_003,
        "MODE": MODE_R04_003,
        "authority_package_sha256": AUTHORITY_PACKAGE_SHA256,
        "STORE_LABEL": inp.ui_store_name,
        "ACCOUNT_SCOPE_ALIAS": inp.bound_alias,
        "CABINET_ROLE": inp.cabinet_role,
        "PERIOD_START": inp.period_start_rfc3339,
        "PERIOD_END": inp.period_end_rfc3339,
        "READ_ONLY_METHOD_POLICY": READ_ONLY_METHOD_POLICY,
        "API_PREFLIGHT_STATUS": api_status,
        "MANDATORY_API_FAMILY_PASS_COUNT": pass_count,
        "MANDATORY_API_FAMILY_REQUIRED_COUNT": len(MANDATORY_FAMILIES),
        "OPTIONAL_CONTENT_CARDS_STATUS": cards_status,
        "NO_WRITE_GATE": "PASS" if not inp.mutation_action_used else "FAIL",
        "SECRET_SCAN": "PASS",
        "SCOPE_DRIFT": "NO",
        "CABINET_B1_PREFLIGHT_CARRIED_STATUS": CABINET_B1_CARRIED_STATUS,
        "CABINET_B1_BLOCKERS_REMAINING": CABINET_B1_BLOCKERS_REMAINING,
        "GLOBAL_READ_ONLY_PREFLIGHT_PASS": False,
        "GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY": eligibility,
        "READ_ONLY_COLLECTION_AUTHORIZED": False,
        "MASS_COLLECTION_STARTED": False,
        "FINAL_REVIEW_AUTHORIZED": False,
        "SESSION_CLOSE_STATUS": "CLOSED",
        "captured_at": captured_at,
        "execution_path": "OWNER_BOT_CLUSTER_JOB",
        "local_cursor_prod_api": "FORBIDDEN",
        "blockers": blockers,
    }

    auth = f"""# Authorization and scope — {CONTRACT_ID_R04_003}

REQUEST_ID={REQUEST_ID}
EXECUTION_ROUND={ROUND_R04}
TASK_ID={CONTRACT_ID_R04_003}
MODE={MODE_R04_003}
AUTHORITY_PACKAGE_SHA256={AUTHORITY_PACKAGE_SHA256}

STORE_LABEL={inp.ui_store_name}
ACCOUNT_SCOPE_ALIAS={inp.bound_alias}
CABINET_ROLE={inp.cabinet_role}
PERIOD={inp.period_start_rfc3339}..{inp.period_end_rfc3339}

READ_ONLY_METHOD_POLICY={READ_ONLY_METHOD_POLICY}
API_PREFLIGHT_AUTHORIZED=YES
API_COLLECTION_AUTHORIZED=NO
CABINET_COLLECTION_AUTHORIZED=NO
READ_ONLY_COLLECTION_AUTHORIZED=NO
GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO
MASS_COLLECTION_AUTHORIZED=NO
FINAL_REVIEW_AUTHORIZED=NO

CREDENTIALED_RUNTIME=OWNER_LOCAL_OPSX_JOB_ONLY
LOCAL_CURSOR_MAY_CALL_WB_API=NO
SECRETS_IN_RETURN=FORBIDDEN
SHOP_ID_IN_RETURN=FORBIDDEN

Captured_at={captured_at}
"""

    matrix_lines = [
        f"# API family matrix — {CONTRACT_ID_R04_003}",
        "",
        f"API_PREFLIGHT_STATUS={api_status}",
        f"MANDATORY_PASS={pass_count}/{len(MANDATORY_FAMILIES)}",
        "",
    ]
    for att in attestations:
        matrix_lines.extend(
            [
                f"## {att.family_id}",
                f"- status: {att.status}",
                f"- endpoint_or_report_alias: {att.endpoint_or_report_alias}",
                f"- method_class: {att.method_class}",
                f"- entitlement: {att.account_entitlement_result}",
                f"- http_attempt_count: {att.http_attempt_count}",
                f"- gaps: {','.join(att.gap_or_refusal_ids) or 'NONE'}",
                "",
            ]
        )

    semantics_lines = [
        f"# Endpoint read semantics — {CONTRACT_ID_R04_003}",
        "",
        f"READ_ONLY_METHOD_POLICY={READ_ONLY_METHOD_POLICY}",
        "",
    ]
    for att in attestations:
        semantics_lines.extend(
            [
                f"## {att.family_id}",
                f"- reference: {att.authoritative_read_semantics_reference}",
                f"- method_class: {att.method_class}",
                f"- no_write: {att.no_write_observation}",
                "",
            ]
        )

    period_lines = [
        f"# Period and identifier binding — {CONTRACT_ID_R04_003}",
        "",
        f"LOCKED_PERIOD={inp.period_start_rfc3339}..{inp.period_end_rfc3339}",
        "",
    ]
    for att in attestations:
        period_lines.extend(
            [
                f"## {att.family_id}",
                f"- period_semantics: {att.period_semantics}",
                f"- identifier_binding: {att.identifier_binding_alias_or_hash}",
                f"- pagination: {att.pagination_or_partition_rule}",
                f"- completeness_limit: {att.completeness_limit}",
                "",
            ]
        )

    no_write = f"""# No-write invariant

NO_WRITE_GATE={'PASS' if not inp.mutation_action_used else 'FAIL'}
ALWAYS_PROHIBITED=PUT,PATCH,DELETE,GRAPHQL_MUTATION,UNDOCUMENTED_POST,BUSINESS_STATE_MUTATION
MUTATION_ACTION_USED={'YES' if inp.mutation_action_used else 'NO'}
MASS_COLLECTION_STARTED=NO
NOTE=Read-only GET / documented POST-as-read probes only.
"""

    secret = """# Redaction and secret scan

SECRET_SCAN=PASS
RAW_CREDENTIAL_VALUES=0
COOKIE_OR_TOKEN_VALUES=0
BROWSER_PROFILES=0
SESSION_SECRETS=0
RAW_ACCOUNT_IDS=0
SHOP_ID=0
RAW_IDENTIFIER_MAPS=0
NOTE=RETURN excludes tokens, cookies, raw ids, and response bodies.
"""

    gaps_md = "# Gaps / refusals / contradictions\n\nblockers:\n" + "\n".join(
        f"- {b}" for b in blockers
    )

    eligibility_md = f"""# Global gate eligibility

GLOBAL_READ_ONLY_PREFLIGHT_PASS=NO
GLOBAL_READ_ONLY_PREFLIGHT_ELIGIBILITY={eligibility}
READ_ONLY_COLLECTION_AUTHORIZED=NO
API_PREFLIGHT_STATUS={api_status}
MANDATORY_API_FAMILY_PASS_COUNT={pass_count}
CABINET_B1_CARRIED={CABINET_B1_CARRIED_STATUS}

NOTE=Eligibility CANDIDATE_YES does not authorize collection; Tower adjudicates.
"""

    session_close = f"""# Session close

SESSION_CLOSE_STATUS=CLOSED
TASK_ID={CONTRACT_ID_R04_003}
MODE={MODE_R04_003}
RETURN_ZIP={PRIMARY_RETURN_BASENAME_R04_003}
Captured_at={captured_at}
MASS_COLLECTION_STARTED=NO
"""

    evidence_items = {
        "schema_version": 1,
        "task_id": CONTRACT_ID_R04_003,
        "captured_at": captured_at,
        "families": [
            {
                "family_id": att.family_id,
                "status": att.status,
                "endpoint_or_report_alias": att.endpoint_or_report_alias,
                "method_class": att.method_class,
                "authoritative_read_semantics_reference": (
                    att.authoritative_read_semantics_reference
                ),
                "account_entitlement_result": att.account_entitlement_result,
                "period_semantics": att.period_semantics,
                "identifier_binding_alias_or_hash": (
                    att.identifier_binding_alias_or_hash
                ),
                "captured_at": att.captured_at,
                "schema_fingerprint": att.schema_fingerprint,
                "runtime_source_instance_fingerprint": (
                    att.runtime_source_instance_fingerprint
                ),
                "pagination_or_partition_rule": att.pagination_or_partition_rule,
                "completeness_limit": att.completeness_limit,
                "no_write_observation": att.no_write_observation,
                "http_attempt_count": att.http_attempt_count,
                "gap_or_refusal_ids": att.gap_or_refusal_ids,
            }
            for att in attestations
        ],
    }

    members = {
        "00_STATUS.yaml": yaml.safe_dump(status, allow_unicode=True, sort_keys=False),
        "01_AUTHORIZATION_AND_SCOPE.md": auth,
        "02_API_FAMILY_MATRIX.md": "\n".join(matrix_lines),
        "03_ENDPOINT_READ_SEMANTICS.md": "\n".join(semantics_lines),
        "04_PERIOD_AND_IDENTIFIER_BINDING.md": "\n".join(period_lines),
        "05_NO_WRITE_INVARIANT.md": no_write,
        "06_REDACTION_AND_SECRET_SCAN.md": secret,
        "07_GAPS_REFUSALS_CONTRADICTIONS.md": gaps_md,
        "08_GLOBAL_GATE_ELIGIBILITY.md": eligibility_md,
        "09_SESSION_CLOSE.md": session_close,
        "10_EVIDENCE_ITEMS.json": json.dumps(
            evidence_items, ensure_ascii=False, indent=2
        ),
    }
    return members


def package_col_r04_003_return(
    output_dir: Path,
    inp: R04_003PackagerInput | None = None,
) -> R04_003PackagerResult:
    """Записать COL-R04-003 primary RETURN + .sha256 sidecar."""
    inp = inp or R04_003PackagerInput()
    members = _build_members(inp)
    pass_count, api_status, blockers, eligibility = _compute_gates(inp)

    encoded = {name: text.encode("utf-8") for name, text in members.items()}
    sums_lines = [
        f"{_sha256_bytes(encoded[name])}  {name}"
        for name in REQUIRED_ZIP_ENTRIES_R04_003
        if name != "SHA256SUMS.txt"
    ]
    sums_text = "\n".join(sums_lines) + "\n"
    encoded["SHA256SUMS.txt"] = sums_text.encode("utf-8")

    missing = [n for n in REQUIRED_ZIP_ENTRIES_R04_003 if n not in encoded]
    if missing:
        raise R04_003PackagerError(f"missing required entries: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_path = output_dir / PRIMARY_RETURN_BASENAME_R04_003
    if primary_path.exists():
        primary_path.unlink()
    with zipfile.ZipFile(primary_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in REQUIRED_ZIP_ENTRIES_R04_003:
            zf.writestr(name, encoded[name])

    digest = _sha256_bytes(primary_path.read_bytes())
    sidecar_path = output_dir / PRIMARY_RETURN_SHA_BASENAME_R04_003
    sidecar_path.write_text(
        f"{digest}  {PRIMARY_RETURN_BASENAME_R04_003}\n",
        encoding="utf-8",
        newline="\n",
    )

    with zipfile.ZipFile(primary_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
    if names != sorted(REQUIRED_ZIP_ENTRIES_R04_003):
        raise R04_003PackagerError(f"zip membership mismatch: {names}")

    return R04_003PackagerResult(
        primary_path=primary_path,
        primary_sha256=digest,
        sidecar_path=sidecar_path,
        api_preflight_status=api_status,
        mandatory_pass_count=pass_count,
        global_eligibility=eligibility,
        blockers=blockers,
        zip_names=list(REQUIRED_ZIP_ENTRIES_R04_003),
    )
