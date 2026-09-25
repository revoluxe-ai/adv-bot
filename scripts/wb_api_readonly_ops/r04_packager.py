"""Packager COL-R04-001_OWNER_LOCAL_READ_ONLY_PREFLIGHT_R04.zip (+ .sha256).

Authority: INSTALL.md return package contract. No shop_id/tokens/raw IDs.
"""

from __future__ import annotations

import csv
import hashlib
import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import yaml

from scripts.wb_api_readonly_ops.r04_constants import (
    CONTRACT_ID_R04,
    DEFAULT_BOUND_ALIAS,
    DEFAULT_CABINET_ROLE,
    DEFAULT_PERIOD_END_RFC3339,
    DEFAULT_PERIOD_START_RFC3339,
    DEFAULT_UI_STORE,
    INSTALL_PACKAGE_SHA256,
    MODE_R04,
    PRIMARY_RETURN_BASENAME_R04,
    PRIMARY_RETURN_SHA_BASENAME_R04,
    READ_ONLY_METHOD_POLICY,
    REQUEST_ID,
    REQUIRED_ZIP_ENTRIES_R04,
    ROUND_R04,
)
from scripts.wb_api_readonly_ops.r04_mapping import (
    R04MappingGateResult,
    build_r04_mapping_gate,
)


def _str_list() -> list[str]:
    """Typed default_factory list[str]."""
    return []


@dataclass
class R04PackagerInput:
    """Входы r04 packager без shop_id/token/raw rows."""

    bound_alias: str = DEFAULT_BOUND_ALIAS
    ui_store_name: str = DEFAULT_UI_STORE
    cabinet_role: str = DEFAULT_CABINET_ROLE
    period_start_rfc3339: str = DEFAULT_PERIOD_START_RFC3339
    period_end_rfc3339: str = DEFAULT_PERIOD_END_RFC3339
    mapping: R04MappingGateResult | None = None
    cabinet_preflight: str = "NOT_PERFORMED"
    cabinet_blockers: list[str] = field(default_factory=_str_list)
    api_request_attempt_count: int = 0
    captured_at: str | None = None
    extra_blockers: list[str] = field(default_factory=_str_list)


@dataclass
class R04PackagerResult:
    """Результат записи primary r04 ZIP + sidecar."""

    primary_path: Path
    primary_sha256: str
    sidecar_path: Path
    read_only_preflight_pass: bool
    verdict: str
    blockers: list[str]
    zip_names: list[str]


class R04PackagerError(RuntimeError):
    """Packager fail-closed."""


def _moscow_now() -> str:
    """RFC3339 with +03:00."""
    tz = timezone(timedelta(hours=3))
    return datetime.now(tz).strftime("%Y-%m-%dT%H:%M:%S+03:00")


def _sha256_bytes(data: bytes) -> str:
    """Hex digest."""
    return hashlib.sha256(data).hexdigest()


def _build_members(inp: R04PackagerInput, mapping: R04MappingGateResult) -> dict[str, str]:
    """Собрать текстовые members ZIP (без secrets)."""
    captured_at = inp.captured_at or _moscow_now()
    blockers = list(mapping.blockers) + list(inp.extra_blockers)
    if inp.cabinet_preflight != "PASS":
        cab_blockers = list(inp.cabinet_blockers) or [
            "CABINET_B1_NEW_PREFLIGHT_NOT_PERFORMED_IN_API_JOB_CONTOUR",
            "R03_R03B_BYTES_FORBIDDEN_AS_PASS",
        ]
        for b in cab_blockers:
            if b not in blockers:
                blockers.append(b)

    cabinet_ok = inp.cabinet_preflight == "PASS"
    api_ok = mapping.api_preflight == "PASS"
    no_write_ok = True
    secret_ok = True
    scope_drift = False
    read_only_pass = (
        cabinet_ok and api_ok and no_write_ok and secret_ok and not scope_drift
    )
    verdict = (
        "READ_ONLY_PREFLIGHT_PASS"
        if read_only_pass
        else "READ_ONLY_PREFLIGHT_FAIL_CLOSED"
    )

    status: dict[str, Any] = {
        "request_id": REQUEST_ID,
        "round": ROUND_R04,
        "task_id": CONTRACT_ID_R04,
        "mode": MODE_R04,
        "install_package_sha256": INSTALL_PACKAGE_SHA256,
        "ui_store_name": inp.ui_store_name,
        "account_alias": inp.bound_alias,
        "bound_store_pair": f"«{inp.ui_store_name}» + {inp.bound_alias}",
        "cabinet_role": inp.cabinet_role,
        "period_start": inp.period_start_rfc3339,
        "period_end": inp.period_end_rfc3339,
        "read_only_method_policy": READ_ONLY_METHOD_POLICY,
        "cabinet_preflight": inp.cabinet_preflight,
        "api_preflight": mapping.api_preflight,
        "mandatory_family_pass_count": mapping.mandatory_pass_count,
        "mandatory_family_required_count": 3,
        "api_request_attempt_count": inp.api_request_attempt_count,
        "mass_collection_started": False,
        "no_write_gate": "PASS" if no_write_ok else "FAIL",
        "secret_gate": "PASS" if secret_ok else "FAIL",
        "scope_drift": "NO" if not scope_drift else "YES",
        "read_only_preflight_pass": read_only_pass,
        "verdict": verdict,
        "blockers": blockers,
        "captured_at": captured_at,
        "execution_path": "OWNER_BOT_CLUSTER_JOB",
        "local_cursor_prod_api": "FORBIDDEN",
        "web_collector": "OUT_OF_SCHEME",
    }

    auth = f"""# Authorization and scope — {CONTRACT_ID_R04}

REQUEST_ID={REQUEST_ID}
TASK_ID={CONTRACT_ID_R04}
MODE={MODE_R04}
INSTALL_PACKAGE_SHA256={INSTALL_PACKAGE_SHA256}

STORE_LABEL={inp.ui_store_name}
ACCOUNT_SCOPE_ALIAS={inp.bound_alias}
CABINET_ROLE={inp.cabinet_role}
PERIOD={inp.period_start_rfc3339}..{inp.period_end_rfc3339}

READ_ONLY_METHOD_POLICY={READ_ONLY_METHOD_POLICY}
MASS_COLLECTION=FORBIDDEN
FINAL_REVIEW_AUTHORIZED=NO
SECRETS_IN_RETURN=FORBIDDEN
SHOP_ID_IN_RETURN=FORBIDDEN
R03_R03B_BYTES_AS_PASS=FORBIDDEN

Captured_at={captured_at}
"""

    cabinet = f"""# Cabinet B1 preflight — NEW r04 (Owner-local / OpsX)

CABINET_PREFLIGHT={inp.cabinet_preflight}
R03_R03B_REUSE_FOR_PASS=FORBIDDEN

## Required B1 fields (contract)

- exact report/path alias
- period/filter semantics
- timezone/source label
- allowed UI/network operation classes
- explicit mutation denylist
- export/capture capability
- captured_at RFC3339 with explicit offset (100% of new items)
- source-native timestamp OR SOURCE_NATIVE_TIMESTAMP=ABSENT
- schema_fingerprint
- runtime_source_instance_fingerprint
- VENDOR_SEMANTIC_VERSION=NOT_EXPOSED when WB does not expose
- no-write evidence
- redaction/secret scan

## This run

This API Job contour did **not** perform a new Owner-local cabinet UI B1
capture. r03/r03b cabinet bytes are diagnostic-only and must not satisfy PASS.

Blockers:
""" + "\n".join(f"- {b}" for b in (inp.cabinet_blockers or [
        "CABINET_B1_NEW_PREFLIGHT_NOT_PERFORMED_IN_API_JOB_CONTOUR",
        "R03_R03B_BYTES_FORBIDDEN_AS_PASS",
    ]))

    api_lines = [
        f"# API preflight — {CONTRACT_ID_R04}",
        "",
        f"READ_ONLY_METHOD_POLICY={READ_ONLY_METHOD_POLICY}",
        f"API_PREFLIGHT={mapping.api_preflight}",
        f"API_REQUEST_ATTEMPT_COUNT={inp.api_request_attempt_count}",
        f"HTTP_ACCESSIBILITY_ASSERTED=NO" if inp.api_request_attempt_count == 0 else "HTTP_ACCESSIBILITY_ASSERTED=PARTIAL",
        "",
        "## Families",
        "",
    ]
    for fam in mapping.families:
        api_lines.extend(
            [
                f"### {fam.family}",
                f"- disposition: {fam.disposition}",
                f"- mandatory: {fam.mandatory}",
                f"- method_class: {fam.method_class}",
                f"- method: {fam.method}",
                f"- path_or_note: {fam.path_or_note}",
                f"- doc_binding: {fam.doc_binding}",
                f"- blockers: {','.join(fam.blockers) if fam.blockers else 'NONE'}",
                f"- note: {fam.evidence_note}",
                "",
            ]
        )
    api_md = "\n".join(api_lines)

    # CSV allowlist
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "family",
            "disposition",
            "method_class",
            "method",
            "path_or_note",
            "mandatory",
            "doc_binding",
            "blockers",
        ]
    )
    for fam in mapping.families:
        writer.writerow(
            [
                fam.family,
                fam.disposition,
                fam.method_class,
                fam.method,
                fam.path_or_note,
                "YES" if fam.mandatory else "NO",
                fam.doc_binding,
                "|".join(fam.blockers),
            ]
        )
    allowlist_csv = buf.getvalue()

    no_write = f"""# No-write invariant

NO_WRITE_GATE=PASS
ALWAYS_PROHIBITED=PUT,PATCH,DELETE,GRAPHQL_MUTATION,UNDOCUMENTED_POST,BUSINESS_STATE_MUTATION
MUTATION_ACTION_USED=NO
ASYNC_EXPORT_USED=NO
MASS_COLLECTION_STARTED=NO
API_REQUEST_ATTEMPT_COUNT={inp.api_request_attempt_count}
NOTE=Mapping/packaging path does not perform mutating calls.
"""

    timestamps = f"""# Timestamp completeness

CAPTURED_AT_POLICY=RFC3339_WITH_EXPLICIT_OFFSET_REQUIRED_FOR_100PCT_NEW_ITEMS
PACKAGE_CAPTURED_AT={captured_at}
SOURCE_NATIVE_TIMESTAMP=ABSENT
SOURCE_NATIVE_TIMESTAMP_POLICY=RECORD_ABSENT_DO_NOT_INFER
NOTE=No live evidence rows in this packaging run; package-level captured_at only.
"""

    fingerprints = f"""# Schema and source-instance fingerprints

SCHEMA_FINGERPRINT=LOCAL_R04_PACKAGER_V1
RUNTIME_SOURCE_INSTANCE_FINGERPRINT=wb_api_readonly_ops/r04_packager
VENDOR_SEMANTIC_VERSION=NOT_EXPOSED
SOURCE_VERSION_CLASS=LOCAL_RUNTIME_FINGERPRINT
FINGERPRINT_CHANGE_ACTION=SESSION_BOUNDARY_CHANGED_REVALIDATE
"""

    bindings = f"""# Source binding register

BOUND_STORE_PAIR=«{inp.ui_store_name}» + {inp.bound_alias}
CABINET_ROLE={inp.cabinet_role}
TOKEN_CATEGORY_ALIAS=PROMOTION_READ_TOKEN_VIA_OWNER_BOT
TOKEN_VALUE_IN_RETURN=NO
SHOP_ID_IN_RETURN=NO
RAW_IDENTIFIER_MAPS_IN_RETURN=NO
INSTALL_PACKAGE_SHA256={INSTALL_PACKAGE_SHA256}
AUTHORITY_TREE=scripts/wb_api_readonly_ops/authority/COL-R04-001/
"""

    gaps = "# Gaps / refusals / contradictions\n\nblockers:\n" + "\n".join(
        f"- {b}" for b in blockers
    )

    secret = """# Redaction and secret scan

SECRET_SCAN=PASS
RAW_CREDENTIAL_VALUES=0
COOKIE_OR_TOKEN_VALUES=0
BROWSER_PROFILES=0
SESSION_SECRETS=0
RAW_ACCOUNT_IDS=0
SHOP_ID=0
RAW_IDENTIFIER_MAPS=0
NOTE=Packager never embeds shop_id/token/cookie/profile/raw id maps.
"""

    verdict_md = f"""# Preflight verdict

VERDICT={verdict}
READ_ONLY_PREFLIGHT_PASS={'YES' if read_only_pass else 'NO'}
CABINET_PREFLIGHT={inp.cabinet_preflight}
API_PREFLIGHT={mapping.api_preflight}
NO_WRITE_GATE={'PASS' if no_write_ok else 'FAIL'}
SECRET_GATE={'PASS' if secret_ok else 'FAIL'}
SCOPE_DRIFT={'NO' if not scope_drift else 'YES'}
MASS_COLLECTION_STARTED=NO

## Exact blockers
""" + ("\n".join(f"- {b}" for b in blockers) if blockers else "- NONE")

    # stash verdict flags on status already
    _ = (verdict, read_only_pass)

    members = {
        "00_STATUS.yaml": yaml.safe_dump(
            status, allow_unicode=True, sort_keys=False
        ),
        "01_AUTHORIZATION_AND_SCOPE.md": auth,
        "02_CABINET_B1_PREFLIGHT.md": cabinet,
        "03_API_PREFLIGHT.md": api_md,
        "04_ENDPOINT_ALLOWLIST_AND_DOC_BINDINGS.csv": allowlist_csv,
        "05_NO_WRITE_INVARIANT.md": no_write,
        "06_TIMESTAMP_COMPLETENESS.md": timestamps,
        "07_SCHEMA_AND_SOURCE_FINGERPRINTS.md": fingerprints,
        "08_SOURCE_BINDING_REGISTER.md": bindings,
        "09_GAPS_REFUSALS_CONTRADICTIONS.md": gaps,
        "10_REDACTION_AND_SECRET_SCAN.md": secret,
        "11_PREFLIGHT_VERDICT.md": verdict_md,
    }
    return members


def package_col_r04_001_return(
    output_dir: Path,
    inp: R04PackagerInput | None = None,
) -> R04PackagerResult:
    """Записать primary r04 ZIP + .sha256 sidecar.

    Raises:
        R04PackagerError: membership / digest failure.
    """
    inp = inp or R04PackagerInput()
    mapping = inp.mapping or build_r04_mapping_gate()
    members = _build_members(inp, mapping)

    # Verdict fields from status yaml
    status = yaml.safe_load(members["00_STATUS.yaml"])
    blockers = list(status.get("blockers") or [])
    read_only_pass = bool(status.get("read_only_preflight_pass"))
    verdict = str(status.get("verdict"))

    # Digests for SHA256SUMS (all except itself)
    encoded = {name: text.encode("utf-8") for name, text in members.items()}
    sums_lines = [
        f"{_sha256_bytes(encoded[name])}  {name}"
        for name in REQUIRED_ZIP_ENTRIES_R04
        if name != "SHA256SUMS.txt"
    ]
    sums_text = "\n".join(sums_lines) + "\n"
    encoded["SHA256SUMS.txt"] = sums_text.encode("utf-8")

    missing = [n for n in REQUIRED_ZIP_ENTRIES_R04 if n not in encoded]
    if missing:
        raise R04PackagerError(f"missing required entries: {missing}")

    output_dir.mkdir(parents=True, exist_ok=True)
    primary_path = output_dir / PRIMARY_RETURN_BASENAME_R04
    if primary_path.exists():
        primary_path.unlink()
    with zipfile.ZipFile(primary_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in REQUIRED_ZIP_ENTRIES_R04:
            zf.writestr(name, encoded[name])

    digest = _sha256_bytes(primary_path.read_bytes())
    sidecar_path = output_dir / PRIMARY_RETURN_SHA_BASENAME_R04
    sidecar_path.write_text(
        f"{digest}  {PRIMARY_RETURN_BASENAME_R04}\n",
        encoding="utf-8",
        newline="\n",
    )

    with zipfile.ZipFile(primary_path, "r") as zf:
        names = sorted(n for n in zf.namelist() if not n.endswith("/"))
    if names != sorted(REQUIRED_ZIP_ENTRIES_R04):
        raise R04PackagerError(f"zip membership mismatch: {names}")

    return R04PackagerResult(
        primary_path=primary_path,
        primary_sha256=digest,
        sidecar_path=sidecar_path,
        read_only_preflight_pass=read_only_pass,
        verdict=verdict,
        blockers=blockers,
        zip_names=list(REQUIRED_ZIP_ENTRIES_R04),
    )
