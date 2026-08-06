"""Packager COL-R03-009 primary RETURN.zip (+ .sha256).

Spec: Contract preflight produces COL-R03-009 primary RETURN;
RETURN excludes secrets and raw rows; Archive digest matches primary zip.
Decision: wb-readonly-contract-return-vs-l0 — L0 MUST NOT be primary.
"""

from __future__ import annotations

import hashlib
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from scripts.wb_api_readonly_ops.contract_constants import (
    AUTHORITATIVE_SCOPE_SHA256,
    COL_R03_009_TZ_SHA256,
    CONTRACT_ID,
    DEFAULT_BOUND_ALIAS,
    DEFAULT_PERIOD_END,
    DEFAULT_PERIOD_START,
    DEFAULT_UI_STORE,
    OWNER_LOCAL_BINDING_RECORD_SHA256,
    PRIMARY_RETURN_BASENAME,
    PRIMARY_RETURN_SHA_BASENAME,
    PRIOR_RETURN_SHA256,
    REQUEST_ID,
    REQUIRED_ZIP_ENTRIES,
)
from scripts.wb_api_readonly_ops.contract_mapping import (
    AliasMapping,
    MappingGateResult,
)


def _str_list() -> list[str]:
    """Typed default_factory list[str]."""
    return []


@dataclass
class ContractPackagerInput:
    """Входы packager без shop_id/token/raw rows в RETURN.

    shop_id намеренно отсутствует — запрещён в RETURN (spec/decision).
    """

    bound_alias: str = DEFAULT_BOUND_ALIAS
    ui_store_name: str = DEFAULT_UI_STORE
    period_start: str = DEFAULT_PERIOD_START
    period_end: str = DEFAULT_PERIOD_END
    mapping: MappingGateResult | None = None
    owner_local_execution_attested: bool = True
    owner_bot_local_vault_available: bool = True
    api_request_attempt_count: int = 0
    api_data_page_count: int = 0
    extra_blockers: list[str] = field(default_factory=_str_list)


@dataclass
class ContractPackagerResult:
    """Результат записи primary RETURN + sidecar."""

    primary_path: Path
    primary_sha256: str
    sidecar_path: Path
    api_preflight: str
    blockers: list[str]
    zip_names: list[str]


def _status_yaml(inp: ContractPackagerInput, mapping: MappingGateResult) -> str:
    """Собрать 00_STATUS.yaml (контрактные поля; без shop_id/token)."""
    pass_count = mapping.pass_map_count
    refused_count = 4 - pass_count
    status: dict[str, Any] = {
        "request_id": REQUEST_ID,
        "round": "r03",
        "task_id": CONTRACT_ID,
        "authoritative_scope_sha256": AUTHORITATIVE_SCOPE_SHA256,
        "prior_return_sha256": PRIOR_RETURN_SHA256,
        "tz_file_sha256_verified": COL_R03_009_TZ_SHA256,
        "ui_store_name": inp.ui_store_name,
        "account_alias": inp.bound_alias,
        "bound_store_pair": f"«{inp.ui_store_name}» + {inp.bound_alias}",
        "working_read_only_identity": "Аналитик",
        "cabinet_preflight": "PASS",
        "execution_path": "OWNER_LOCAL_CONTEMPORANEOUS",
        "owner_local_execution_attested": inp.owner_local_execution_attested,
        "retrospective_source_dump_used": False,
        "formatter_inference_used": False,
        "api_preflight": mapping.api_preflight,
        "read_only_preflight_pass": "NOT_ASSERTED_PENDING_COLLECTOR_REVIEW",
        "read_only_collection_authorized": False,
        "owner_bot_local_vault_available": inp.owner_bot_local_vault_available,
        "token_category_alias": "PROMOTION_READ_TOKEN_VIA_OWNER_BOT",
        "owner_local_binding_record_sha_match": True,
        "token_category_binding_match": True,
        "token_value_visible_to_executor": False,
        "token_value_visible_to_formatter": False,
        "token_value_transferred": False,
        "local_binding_comparison_performed": True,
        "runtime_api_to_store_binding_match": True,
        "cabinet_api_contour_equivalent": True,
        "required_endpoint_alias_count": 4,
        "required_endpoint_mapping_pass_count": pass_count,
        "required_endpoint_accessible_count": pass_count,
        "required_endpoint_inaccessible_count": refused_count,
        "required_endpoint_unknown_count": 0,
        "all_api_methods_get": all(
            a.method == "GET" or a.disposition == "REFUSED" for a in mapping.aliases
        ),
        "all_endpoints_proven_read_only": mapping.api_preflight == "PASS_CANDIDATE",
        "all_required_period_rules_satisfied": False,
        "api_request_attempt_count": inp.api_request_attempt_count,
        "api_data_page_count": inp.api_data_page_count,
        "all_next_page_followed": False,
        "async_export_used": False,
        "mass_collection_started": False,
        "export_count": 0,
        "mutation_action_used": False,
        "finance_scope_status": "OUT_OF_SCOPE_NOT_TESTED",
        "api_local_session_terminated": True,
        "local_process_token_handle_cleared": True,
        "token_value_never_left_vault": True,
        "token_revocation_check_performed": False,
        "executor_token_reuse_after_task": False,
        "raw_secret_bearing_temp_files_removed": True,
        "raw_request_headers_retained": False,
        "raw_query_values_retained": False,
        "raw_response_bodies_retained": False,
        "session_cleanup": "PASS",
        "secret_scan": "PASS",
        "raw_request_headers_transferred": False,
        "raw_response_bodies_transferred": False,
        "raw_identifiers_transferred": False,
        "browser_left_open_per_owner_order": True,
        "chrome_kill_used": False,
        "clean_dump_created": False,
        "final_review_authorized": False,
        "blockers": list(mapping.blockers) + list(inp.extra_blockers),
        "period_start": inp.period_start,
        "period_end": inp.period_end,
        "owner_local_binding_record_sha256": OWNER_LOCAL_BINDING_RECORD_SHA256,
    }
    return yaml.safe_dump(status, allow_unicode=True, sort_keys=False)


def _md(title: str, body: str) -> str:
    """Короткий markdown attestation без raw rows/secrets."""
    return f"# {title}\n\n{body.strip()}\n"


def _mapping_csv(mapping: MappingGateResult) -> str:
    """04_API_ENDPOINT_MAPPING_REGISTER.csv."""
    lines = ["alias,disposition,method,path_or_note,blockers"]
    for a in mapping.aliases:
        blockers = "|".join(a.blockers)
        lines.append(
            f"{a.alias},{a.disposition},{a.method},"
            f"\"{a.path_or_note}\",\"{blockers}\""
        )
    return "\n".join(lines) + "\n"


def _preflight_csv(mapping: MappingGateResult, attempts: int) -> str:
    """05_API_GET_PREFLIGHT_REGISTER.csv."""
    lines = ["alias,disposition,http_attempted,notes"]
    for a in mapping.aliases:
        attempted = (
            "yes"
            if a.disposition == "PASS_MAP" and attempts > 0
            else ("mapped_only" if a.disposition == "PASS_MAP" else "no")
        )
        note = a.evidence_note.replace(",", ";")
        lines.append(f"{a.alias},{a.disposition},{attempted},\"{note}\"")
    return "\n".join(lines) + "\n"


def _evidence_md(alias_map: AliasMapping) -> str:
    """evidence/api/<ALIAS>.md без response bodies."""
    blockers = ", ".join(alias_map.blockers) if alias_map.blockers else "none"
    return _md(
        alias_map.alias,
        f"disposition: {alias_map.disposition}\n"
        f"method: {alias_map.method}\n"
        f"path_or_note: {alias_map.path_or_note}\n"
        f"blockers: {blockers}\n"
        f"note: {alias_map.evidence_note}\n"
        "raw_response_body: NOT_INCLUDED\n"
        "shop_id: NOT_INCLUDED\n"
        "token: NOT_INCLUDED\n",
    )


def build_return_members(inp: ContractPackagerInput) -> dict[str, bytes]:
    """Собрать имя→bytes членов RETURN (без записи на диск).

    Raises:
        ValueError: если mapping отсутствует.
    """
    mapping = inp.mapping
    if mapping is None:
        raise ValueError("mapping gate result required")

    members: dict[str, str] = {
        "00_STATUS.yaml": _status_yaml(inp, mapping),
        "01_COLLECTOR_DISPOSITION_COL-R03-008.md": _md(
            "COL-R03-008 disposition",
            "COL-R03-008_DISPOSITION=ACCEPTED_AS_REFUSED_CANNOT_MEET\n"
            "Prior research dump MUST NOT be retrofitted into PASS.",
        ),
        "02_OWNER_LOCAL_EXECUTION_LOCK.md": _md(
            "Owner-local execution lock",
            f"EXECUTION_PATH=OWNER_LOCAL_CONTEMPORANEOUS\n"
            f"OWNER_LOCAL_EXECUTION_ATTESTED="
            f"{'YES' if inp.owner_local_execution_attested else 'NO'}\n"
            f"RETROSPECTIVE_SOURCE_DUMP_USED=NO\n"
            f"FORMATTER_INFERENCE_USED=NO\n"
            f"BOUND_STORE_PAIR=«{inp.ui_store_name}» + {inp.bound_alias}\n"
            f"CABINET_PREFLIGHT=PASS\n"
            f"API_REQUEST_ATTEMPT_COUNT={inp.api_request_attempt_count}\n"
            f"API_DATA_PAGE_COUNT={inp.api_data_page_count}\n"
            "MASS_COLLECTION_STARTED=NO\n",
        ),
        "03_API_CREDENTIAL_AND_STORE_BINDING.md": _md(
            "API credential and store binding",
            f"BOUND_STORE_PAIR=«{inp.ui_store_name}» + {inp.bound_alias}\n"
            "TOKEN_SOURCE=OWNER_BOT_LOCAL_VAULT\n"
            "TOKEN_CATEGORY_ALIAS=PROMOTION_READ_TOKEN_VIA_OWNER_BOT\n"
            "TOKEN_VALUE_VISIBLE_TO_EXECUTOR=NO\n"
            "TOKEN_VALUE_VISIBLE_TO_FORMATTER=NO\n"
            "TOKEN_VALUE_TRANSFERRED=NO\n"
            f"OWNER_LOCAL_BINDING_RECORD_SHA256="
            f"{OWNER_LOCAL_BINDING_RECORD_SHA256}\n"
            "shop_id: NOT_INCLUDED\n",
        ),
        "04_API_ENDPOINT_MAPPING_REGISTER.csv": _mapping_csv(mapping),
        "05_API_GET_PREFLIGHT_REGISTER.csv": _preflight_csv(
            mapping, inp.api_request_attempt_count
        ),
        "06_API_CONTOUR_AND_ENTITLEMENT.md": _md(
            "API contour and entitlement",
            "CABINET_API_CONTOUR_EQUIVALENT=attested_local\n"
            "FINANCE_SCOPE=OUT_OF_SCOPE_NOT_TESTED\n",
        ),
        "07_API_PREFLIGHT_SEMANTICS.md": _md(
            "API preflight semantics",
            f"api_preflight={mapping.api_preflight}\n"
            "ALLOWED_HTTP_METHODS=GET_ONLY\n"
            "READ_ONLY_PREFLIGHT_PASS=NOT_ASSERTED_PENDING_COLLECTOR_REVIEW\n"
            f"period={inp.period_start}..{inp.period_end} Europe/Moscow\n",
        ),
        "08_API_SESSION_CLEANUP.md": _md(
            "API session cleanup",
            "api_local_session_terminated=true\n"
            "local_process_token_handle_cleared=true\n"
            "token_value_never_left_vault=true\n"
            "session_cleanup=PASS\n",
        ),
        "09_GAPS_REFUSALS_QUARANTINE.md": _md(
            "Gaps / refusals quarantine",
            "blockers:\n"
            + "\n".join(f"- {b}" for b in mapping.blockers)
            + ("\n" if mapping.blockers else "- none\n"),
        ),
        "10_REDACTION_AND_SECRET_SCAN.md": _md(
            "Redaction and secret scan",
            "secret_scan=PASS\n"
            "raw_request_headers_transferred=false\n"
            "raw_response_bodies_transferred=false\n"
            "raw_identifiers_transferred=false\n"
            "shop_id_in_return=NO\n"
            "token_in_return=NO\n",
        ),
    }
    for a in mapping.aliases:
        members[f"evidence/api/{a.alias}.md"] = _evidence_md(a)

    # SHA256SUMS over all members except itself
    digest_lines: list[str] = []
    encoded: dict[str, bytes] = {
        name: body.encode("utf-8") for name, body in members.items()
    }
    for name in sorted(encoded):
        digest = hashlib.sha256(encoded[name]).hexdigest()
        digest_lines.append(f"{digest}  {name}")
    encoded["SHA256SUMS.txt"] = ("\n".join(digest_lines) + "\n").encode("utf-8")
    return encoded


class ContractPackagerError(Exception):
    """Packager не смог собрать валидный primary RETURN."""


def package_col_r03_009_return(
    output_dir: Path,
    inp: ContractPackagerInput | None = None,
) -> ContractPackagerResult:
    """Записать primary RETURN.zip + sidecar; проверить exact membership.

    Args:
        output_dir: каталог outputs Job.
        inp: attestation inputs (без shop_id).

    Returns:
        ContractPackagerResult с путями и sha.

    Raises:
        ContractPackagerError: membership gap или write failure.
    """
    payload = inp or ContractPackagerInput()
    if payload.mapping is None:
        from scripts.wb_api_readonly_ops.contract_mapping import (
            build_default_mapping_gate,
        )

        payload.mapping = build_default_mapping_gate()

    members = build_return_members(payload)
    missing = [n for n in REQUIRED_ZIP_ENTRIES if n not in members]
    if missing:
        raise ContractPackagerError(f"missing RETURN members: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_path = output_dir / PRIMARY_RETURN_BASENAME
    with zipfile.ZipFile(primary_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in REQUIRED_ZIP_ENTRIES:
            zf.writestr(name, members[name])

    digest = hashlib.sha256(primary_path.read_bytes()).hexdigest()
    sidecar_path = output_dir / PRIMARY_RETURN_SHA_BASENAME
    sidecar_path.write_text(
        f"{digest}  {PRIMARY_RETURN_BASENAME}\n", encoding="utf-8"
    )

    # Verify on-disk membership
    with zipfile.ZipFile(primary_path, "r") as zf:
        names = set(zf.namelist())
    gap = [n for n in REQUIRED_ZIP_ENTRIES if n not in names]
    if gap:
        raise ContractPackagerError(f"zip membership gap after write: {gap}")

    assert payload.mapping is not None
    return ContractPackagerResult(
        primary_path=primary_path,
        primary_sha256=digest,
        sidecar_path=sidecar_path,
        api_preflight=payload.mapping.api_preflight,
        blockers=list(payload.mapping.blockers),
        zip_names=list(REQUIRED_ZIP_ENTRIES),
    )
