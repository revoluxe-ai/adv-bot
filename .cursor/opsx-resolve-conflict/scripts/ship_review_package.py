#!/usr/bin/env python3
"""Atomic ship for OPSX resolve-conflict review packages (R25).

Guarantees:
1. CLEAN_UNPACK / PACKAGE_INDEX package_digest == MANIFEST / TRUST_ANCHOR
2. In-archive archive_sha256 is null (external_test_report_only binding)
3. External TEST_REPORT next to ZIP binds delivered archive SHA-256
4. Clean-unpack pytest runs from the extracted ZIP with --confcutdir=tests
5. ZIP is finalized before tests and never rebuilt after tests
6. SIDECAR + TEST_REPORT.log delivered; post-test ZIP re-hash must match
7. Lineage separates origin_source_commit vs host_contract_snapshot_commit
8. Inner operator docs omit self-referential bundle/archive/test totals
9. Post-build validator enforces portability + claim consistency on all
   operator/review documents (not only REVIEW_REQUEST.md)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from path_workspace import (  # noqa: E402
    assert_native_io_path,
    native_artifact_root,
    platform_id,
    scan_source_for_hardcoded_windows_temp,
)
from build_preview_evidence import (  # noqa: E402
    build_preview_evidence_for_ship,
    validate_preview_evidence_artifacts,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
OUT_DIR = native_artifact_root()
PACKAGE_VERSION = "0.40.0"
PACKAGE_NAME = "OPSX_RESOLVE_CONFLICT_COMMAND_001_R40"
REVISION = "R40"
PLATFORM_DECISION_ID = "ADR-OPSX-RC-PLATFORM-001"
PLATFORM_DISPOSITION = "WINDOWS_PREVIEW_ONLY"

# Fragments assembled at import so this source never embeds contiguous
# forbidden path literals (self-scan of .py must remain clean).
_U = "Users"
_H = "home"
_MR = "meta" + "-repo"
_AB = "adv" + "-bot"
_FORBIDDEN_PATH_RES = (
    re.compile(rf"(?i)[A-Z]:\\{_U}\\"),
    re.compile(rf"(?i)/{_U}/"),
    re.compile(rf"(?i)/{_H}/"),
    re.compile(rf"(?i){_MR}\\{_AB}"),
    re.compile(rf"(?i){_MR}/{_AB}"),
)
_STALE_CLAIM_RES = (
    re.compile(r"(?im)^\s*bundle_sha256\s*=\s*[0-9a-f]{64}\s*$"),
    re.compile(r"(?im)^\s*inner_zip_sha256\s*=\s*[0-9a-f]{64}\s*$"),
    re.compile(r"(?im)^\s*inner_archive_sha256\s*=\s*[0-9a-f]{64}\s*$"),
    re.compile(r"(?im)clean_unpack\s*=\s*\d+\s+passed"),
    re.compile(r"(?i)\b\d+\s+passed,\s*\d+\s+skipped\b"),
    # Markdown / prose delivery claims (R24 README failure mode).
    re.compile(r"(?i)bundle_sha256[`\s:=]+[`']?[0-9a-f]{64}"),
    re.compile(r"(?i)inner(?:_|\s+)?zip(?:\s+sha)?[`\s:=]+[`']?[0-9a-f]{64}"),
    re.compile(r"(?i)inner_archive_sha256[`\s:=]+[`']?[0-9a-f]{64}"),
    re.compile(r"(?i)clean[-_ ]?unpack[`\s:=]+.*\d+\s+passed"),
    re.compile(r"(?i)package_digest[`\s:=]+[`']?[0-9a-f]{64}"),
)
_OPERATOR_DOC_SUFFIXES = (".md", ".txt")
_OPERATOR_DOC_NAMES = {
    "review_request.md",
    "readme_review.md",
    "authorship.md",
    "00_scope.md",
    "01_review_standard.md",
    "02_required_context.md",
    "03_verdict_schema.md",
}
_HISTORICAL_MARKER = "HISTORICAL_BASELINE_ALLOWLIST"


def restore_host_contracts_from_origin() -> None:
    """Force host_frozen_contracts bytes to match origin_source_commit.

    Ship must not mint unsigned provenance. Paths absent from origin must be
    removed from host_frozen_contracts / host_contract_sha256 / required_repo_paths
    before lineage (not auto-approved).
    """
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    origin = str(
        manifest.get("origin_source_commit") or manifest.get("source_commit") or ""
    ).strip()
    if not origin:
        origin = subprocess.check_output(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            text=True,
        ).strip()
        manifest["origin_source_commit"] = origin
        manifest["source_commit"] = origin
    categories = manifest.get("input_categories") or {}
    package_owned = list(categories.get("package_owned_required") or [])
    # Prefer existing frozen list; fall back to required paths minus package-owned.
    host_list = list(categories.get("host_frozen_contracts") or [])
    if not host_list:
        host_list = [
            rel
            for rel in (manifest.get("required_repo_paths") or [])
            if isinstance(rel, str) and rel not in package_owned
        ]
    # Also drop stale host_contract_sha256 keys that are no longer frozen.
    prior_hashes = manifest.get("host_contract_sha256") or {}
    if isinstance(prior_hashes, dict):
        for rel in prior_hashes:
            if isinstance(rel, str) and rel not in host_list:
                host_list.append(rel)
    kept: list[str] = []
    removed: list[str] = []
    host_hashes: dict[str, str] = {}
    for rel in host_list:
        if not isinstance(rel, str):
            continue
        proc = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show", f"{origin}:{rel}"],
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            removed.append(rel)
            continue
        wt = REPO_ROOT / rel
        wt.parent.mkdir(parents=True, exist_ok=True)
        wt.write_bytes(proc.stdout)
        kept.append(rel)
        host_hashes[rel] = hashlib.sha256(proc.stdout).hexdigest()
    categories["host_frozen_contracts"] = kept
    categories.setdefault(
        "package_owned_required",
        [
            ".cursor/commands/opsx-resolve-conflict.md",
            ".cursor/opsx-resolve-conflict/process_surfaces.json",
        ],
    )
    package_owned = list(categories["package_owned_required"])
    manifest["input_categories"] = categories
    manifest["host_contract_sha256"] = host_hashes
    manifest["required_repo_paths"] = sorted(set(package_owned) | set(kept))
    if removed:
        manifest.setdefault("lineage_notes", {})
        manifest["lineage_notes"]["removed_from_host_frozen_absent_origin"] = removed
    (PACKAGE_ROOT / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    # Clear any ambient ship-generated provenance env (forbidden channel).
    os.environ.pop("OPSX_LINEAGE_SIGNED_PROVENANCE", None)


def sha256_file(path: Path) -> str:
    """Return SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_inner_review_request() -> None:
    """Write inner REVIEW_REQUEST without self-referential delivery digests."""
    text = f"""# REPEAT REVIEW REQUEST — `/opsx-resolve-conflict` {REVISION} / {PACKAGE_VERSION}

Review package (single delivery archive):

```text
<NATIVE_ARTIFACT_ROOT>/{PACKAGE_NAME}_REVIEW_BUNDLE.zip

{PACKAGE_NAME}
PACKAGE_VERSION={PACKAGE_VERSION}
CONTRACT_SCHEMA_VERSION=opsx-resolve-conflict/v2
AUTHOR=Cursor
STATUS=preview_only_no_go
GO_CAPABILITY=false
SAFE_USAGE_SCOPE=PREVIEW_ONLY
```

## Delivery digests (external only)

This **inner** document intentionally omits:

- outer review-bundle SHA-256;
- inner review ZIP SHA-256;
- external clean-unpack pass/skip totals.

Authoritative values for those fields are only in external evidence:

- `BUNDLE_INDEX.json`
- `{PACKAGE_NAME}.TEST_REPORT.json`
- `{PACKAGE_NAME}.SIDECAR.json`

Package digest for the immutable inner tree is recorded in `MANIFEST.json`,
`TRUST_ANCHOR.json`, and `SHA256SUMS` and must match those artifacts.

## Claimed closures for {REVISION}

1. R38-GATE-PROCESS-001: PREVIEW evidence path sanitization (`<TRUSTED_GIT_EXECUTABLE>`)
2. Recursive JSON string-value path scan (closes R38 JSON-escaping validator bypass)
3. Real merge/rebase PREVIEW evidence rebuilt without author-profile paths
4. Executable digests preserved; `atomicity_claim=false`; R25-MEDIUM-002 remains open
5. R34 `preview_readonly_git.py` sealed; `preview_context`/`preview_advisory` re-pinned for R40; R33–R38 retained closures unchanged
6. `GO_CAPABILITY` remains false; `SAFE_USAGE_SCOPE=PREVIEW_ONLY`

## Architect-closed, pending reviewer confirmation

- R25-HIGH-001
- R25-HIGH-002
- R25-HIGH-003
- R25-MEDIUM-001
- R25-MEDIUM-003 (R30/R31 trust-store path protection)
- R25-MEDIUM-004 (portability + Windows-only platform ADR)

## Still open

- R25-MEDIUM-002 (trusted-Git boundary is **not** atomic; do not treat as closed)
- R25-PROCESS-001
- `BLOCKER_AUTHORITY_PRODUCER_MISSING`
- `BLOCKER_OS_SANDBOX_RUNNER_MISSING`

Perform all three levels and return one verdict from `03_VERDICT_SCHEMA.md`.
"""
    path = PACKAGE_ROOT / "REVIEW_REQUEST.md"
    path.write_text(text, encoding="utf-8")
    scan_text_for_forbidden_claims(text, label="inner REVIEW_REQUEST.md")
    scan_text_for_forbidden_paths(text, label="inner REVIEW_REQUEST.md")


def is_operator_review_document(name: str, text: str) -> bool:
    """Return True if path is an operator/review doc subject to claim scanning."""
    base = Path(name).name.lower()
    if _HISTORICAL_MARKER in text:
        return False
    if base in _OPERATOR_DOC_NAMES:
        return True
    if base.startswith("readme") and base.endswith(".md"):
        return True
    if "review" in base and base.endswith(_OPERATOR_DOC_SUFFIXES):
        return True
    if base.endswith("summary.md") or base.endswith("summary.txt"):
        return True
    return False


def scan_text_for_forbidden_paths(text: str, *, label: str) -> None:
    """Fail closed if author/user workspace paths appear."""
    author_repo = str(REPO_ROOT.resolve())
    author_pkg = str(PACKAGE_ROOT.resolve())
    if author_repo and author_repo in text:
        raise SystemExit(f"validator STOP: author repo path in {label}")
    if author_pkg and author_pkg in text:
        raise SystemExit(f"validator STOP: author package path in {label}")
    for cre in _FORBIDDEN_PATH_RES:
        if cre.search(text):
            raise SystemExit(f"validator STOP: forbidden path pattern in {label}")


def scan_text_for_forbidden_claims(
    text: str,
    *,
    label: str,
    allowed_package_digest: str | None = None,
) -> None:
    """Fail closed if self-referential bundle/archive/test totals are embedded."""
    for cre in _STALE_CLAIM_RES:
        match = cre.search(text)
        if not match:
            continue
        # Allow current package_digest only when it matches MANIFEST digest.
        if "package_digest" in cre.pattern and allowed_package_digest:
            hexes = re.findall(r"[0-9a-f]{64}", match.group(0).lower())
            if hexes and all(h == allowed_package_digest.lower() for h in hexes):
                continue
        raise SystemExit(
            f"validator STOP: self-referential/stale delivery claim in {label}: "
            f"{cre.pattern}"
        )


def assert_native_out_dir() -> bool:
    """Return True when OUT_DIR is acceptable for native I/O on this host."""
    try:
        assert_native_io_path(OUT_DIR, role="OUT_DIR")
    except SystemExit:
        return False
    return True


def validate_shipping_scripts_portability() -> None:
    """Fail closed on hardcoded foreign temp I/O and mixed-separator build paths."""
    for name in (
        "ship_review_package.py",
        "build_review_archive.py",
        "build_replay_evidence.py",
        "build_preview_evidence.py",
        "path_workspace.py",
    ):
        path = PACKAGE_ROOT / "scripts" / name
        text = path.read_text(encoding="utf-8")
        scan_source_for_hardcoded_windows_temp(text, label=str(path))
        # Reject literal Windows temp assignments remaining in shipping sources.
        if "Path(r\"C:\\Temp\")" in text or "Path(r'C:\\Temp')" in text:
            raise SystemExit(
                f"validator STOP: foreign Windows temp Path in shipping script: {name}"
            )


def build_platform_capability_matrix(
    *,
    windows_report: dict | None = None,
    include_native_root: bool = False,
) -> dict:
    """Build ADR Windows-only platform matrix (linux/macos UNSUPPORTED)."""
    import sys

    unsupported_note = (
        "UNSUPPORTED under ADR-OPSX-RC-PLATFORM-001 / APPROVE_WINDOWS_ONLY. "
        "Non-Windows execution fails closed with UNSUPPORTED_PLATFORM. "
        "Enablement requires a separate architecture-change request."
    )
    windows_status = "SUPPORTED"
    if windows_report and windows_report.get("pytest_exit_code") == 0:
        windows_status = "PREVIEW_ONLY_VERIFIED"
    elif windows_report is not None:
        windows_status = "FAILED"
    matrix: dict = {
        "schema": "opsx-resolve-conflict/platform-capability-matrix/v2",
        "decision_id": PLATFORM_DECISION_ID,
        "disposition": PLATFORM_DISPOSITION,
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "supported_platforms": ["windows"],
        "operational_scope": "PREVIEW_ONLY",
        "host_platform": platform_id(),
        "host_python": sys.version.split()[0],
        "platforms": {
            "windows": {
                "status": windows_status,
                "support_claim": "preview_only",
                "full_suite": windows_report,
            },
            "linux": {
                "status": "UNSUPPORTED",
                "support_claim": "unsupported",
                "full_suite": None,
                "note": unsupported_note,
            },
            "macos": {
                "status": "UNSUPPORTED",
                "support_claim": "unsupported",
                "full_suite": None,
                "note": unsupported_note,
            },
        },
        "linux_enablement": "separate_architecture_change_request",
        "go_capability": False,
        "safe_usage_scope": "PREVIEW_ONLY",
    }
    if include_native_root:
        matrix["native_artifact_root"] = str(OUT_DIR)
    return matrix


def write_immutable_platform_matrix() -> Path:
    """Write policy matrix into package context before archive freeze."""
    matrix = build_platform_capability_matrix(windows_report=None)
    # Inner package must not embed author-local OUT_DIR absolute paths.
    pkg_copy = PACKAGE_ROOT / "context" / "PLATFORM_CAPABILITY_MATRIX.json"
    _write_json(pkg_copy, matrix)
    return pkg_copy


def write_external_platform_matrix(*, windows_report: dict | None) -> Path:
    """Write evidence matrix next to shipped artifacts (outer bundle member)."""
    matrix = build_platform_capability_matrix(
        windows_report=windows_report,
        include_native_root=True,
    )
    path = OUT_DIR / f"{PACKAGE_NAME}.PLATFORM_CAPABILITY_MATRIX.json"
    _write_json(path, matrix)
    return path


def assert_matrix_windows_only(matrix: dict, *, label: str) -> None:
    """Fail closed if matrix claims non-Windows support."""
    if matrix.get("decision_id") != PLATFORM_DECISION_ID:
        raise SystemExit(f"validator STOP: {label} missing {PLATFORM_DECISION_ID}")
    if matrix.get("disposition") != PLATFORM_DISPOSITION:
        raise SystemExit(f"validator STOP: {label} disposition mismatch")
    if matrix.get("supported_platforms") != ["windows"]:
        raise SystemExit(f"validator STOP: {label} supported_platforms must be [windows]")
    platforms = matrix.get("platforms") or {}
    for name in ("linux", "macos"):
        row = platforms.get(name) or {}
        if row.get("status") != "UNSUPPORTED":
            raise SystemExit(
                f"validator STOP: {label} {name} must be UNSUPPORTED, got {row.get('status')}"
            )
        if row.get("support_claim") != "unsupported":
            raise SystemExit(
                f"validator STOP: {label} {name} support_claim must be unsupported"
            )
    win = platforms.get("windows") or {}
    if win.get("support_claim") != "preview_only":
        raise SystemExit(
            f"validator STOP: {label} windows support_claim must be preview_only"
        )
    if win.get("status") not in ("SUPPORTED", "PREVIEW_ONLY_VERIFIED"):
        raise SystemExit(
            f"validator STOP: {label} windows status must be "
            f"SUPPORTED|PREVIEW_ONLY_VERIFIED"
        )


def maybe_run_linux_clean_unpack_evidence(
    *,
    zip_path: Path,
    package_digest: str,
    archive_sha: str,
) -> dict | None:
    """Run clean-unpack under WSL when available; return Linux report or None."""
    wsl = shutil.which("wsl")
    if not wsl:
        return {
            "platform": "linux",
            "status": "SKIPPED",
            "reason": "wsl_not_available",
            "pytest_exit_code": None,
            "package_digest": package_digest,
            "archive_sha256": archive_sha,
        }
    # Map Windows path to WSL /mnt/<drive>/...
    win = str(zip_path.resolve())
    drive, rest = os.path.splitdrive(win)
    if not drive:
        return {
            "platform": "linux",
            "status": "SKIPPED",
            "reason": "cannot_map_windows_path_to_wsl",
            "pytest_exit_code": None,
        }
    letter = drive[0].lower()
    wsl_zip = "/mnt/" + letter + rest.replace("\\", "/")
    wsl_out = f"/tmp/{PACKAGE_NAME}_LINUX_CLEAN_UNPACK"
    # Frozen git_typed bind ancestry requires every path component owner to match
    # getuid(). On typical Linux, `/` and `/home` are root-owned, so a non-root
    # user cannot bind trusted Git. Evidence therefore runs as root inside WSL
    # (evidence-only; package GO_CAPABILITY remains false).
    script = f"""
set -e
rm -rf {wsl_out}
mkdir -p {wsl_out}
python3 -m zipfile -e '{wsl_zip}' {wsl_out}
cd {wsl_out}/candidate/.cursor/opsx-resolve-conflict
python3 -m venv .venv
. .venv/bin/activate
pip install -q pytest cryptography pyyaml
export PYTHONPATH=runtime
# Bind root must not sit under world-writable /tmp (GIT_TRUST_BIND_PERMS_UNSAFE).
export OPSX_CONFLICT_STATE=/root/{PACKAGE_NAME}_STATE
export TMPDIR=/root/{PACKAGE_NAME}_TMP
mkdir -p "$OPSX_CONFLICT_STATE" "$TMPDIR"
chmod 700 "$OPSX_CONFLICT_STATE" "$TMPDIR"
python -m pytest tests -q --confcutdir=tests
"""
    log_path = OUT_DIR / f"{PACKAGE_NAME}.LINUX_CLEAN_UNPACK.log"
    proc = subprocess.run(
        [wsl, "-u", "root", "-e", "bash", "-lc", script],
        capture_output=True,
        text=True,
        check=False,
    )
    log_path.write_text(
        (proc.stdout or "") + "\n" + (proc.stderr or ""),
        encoding="utf-8",
    )
    # Parse pytest summary if present.
    passed = skipped = None
    for line in (proc.stdout or "").splitlines()[::-1]:
        m = re.search(r"(\d+)\s+passed(?:,\s*(\d+)\s+skipped)?", line)
        if m:
            passed = int(m.group(1))
            skipped = int(m.group(2) or 0)
            break
    note = None
    if proc.returncode != 0:
        note = (
            "Linux clean-unpack did not fully pass under frozen git_typed bind "
            "ancestry (owner==getuid and no world-writable components on every "
            "ancestor). Stock Linux `/`/`/home` are root-owned for non-root; "
            "root+`/root` state leaves residual trust/symlink failures. "
            "Fixing this requires Git execution architecture changes "
            "(prohibited in R32)."
        )
    return {
        "platform": "linux",
        "status": "VERIFIED" if proc.returncode == 0 else "FAILED",
        "passed": passed,
        "skipped": skipped,
        "pytest_exit_code": proc.returncode,
        "package_digest": package_digest,
        "archive_sha256": archive_sha,
        "log_path": str(log_path),
        "native_artifact_root": f"/root/{PACKAGE_NAME}_TMP",
        "wsl_zip": wsl_zip,
        "runner": "wsl-root",
        "note": note,
    }


def validate_review_bundle(
    *,
    bundle_path: Path,
    package_digest: str,
    archive_sha: str,
    report_path: Path,
) -> None:
    """Post-build validator for final REVIEW_BUNDLE invariants."""
    validate_shipping_scripts_portability()
    if not assert_native_out_dir():
        raise SystemExit("validator STOP: OUT_DIR is not a native filesystem path")
    if not bundle_path.is_file():
        raise SystemExit("validator STOP: review bundle missing")
    with zipfile.ZipFile(bundle_path) as zf:
        index = json.loads(zf.read("BUNDLE_INDEX.json").decode("utf-8"))
        if index.get("package_name") != PACKAGE_NAME:
            raise SystemExit("validator STOP: BUNDLE_INDEX package_name mismatch")
        if index.get("package_version") != PACKAGE_VERSION:
            raise SystemExit("validator STOP: BUNDLE_INDEX package_version mismatch")
        if index.get("go_capability") is not False:
            raise SystemExit("validator STOP: BUNDLE_INDEX go_capability must be false")
        if index.get("inner_archive_sha256") != archive_sha:
            raise SystemExit("validator STOP: BUNDLE_INDEX inner hash mismatch")
        if index.get("package_digest") != package_digest:
            raise SystemExit("validator STOP: BUNDLE_INDEX package_digest mismatch")
        members = {m["path"]: m for m in index.get("members") or []}
        inner_name = f"{PACKAGE_NAME}.zip"
        for name, meta in members.items():
            raw = zf.read(name)
            digest = hashlib.sha256(raw).hexdigest()
            if digest != meta.get("sha256"):
                raise SystemExit(f"validator STOP: member hash mismatch: {name}")
            if len(raw) != int(meta.get("bytes", -1)):
                raise SystemExit(f"validator STOP: member size mismatch: {name}")
        if inner_name not in members:
            raise SystemExit("validator STOP: inner ZIP missing from bundle")
        if hashlib.sha256(zf.read(inner_name)).hexdigest() != archive_sha:
            raise SystemExit("validator STOP: inner ZIP bytes != claimed archive_sha")

        matrix_name = f"{PACKAGE_NAME}.PLATFORM_CAPABILITY_MATRIX.json"
        if matrix_name not in members:
            raise SystemExit(
                "validator STOP: platform capability matrix missing from review bundle"
            )
        outer_matrix = json.loads(zf.read(matrix_name).decode("utf-8"))
        assert_matrix_windows_only(outer_matrix, label="bundle matrix")
        with zipfile.ZipFile(zf.open(inner_name)) as inner:
            inner_matrix_path = (
                "candidate/.cursor/opsx-resolve-conflict/context/"
                "PLATFORM_CAPABILITY_MATRIX.json"
            )
            # Staging also copies matrix at context/ root in some layouts.
            candidates = [
                inner_matrix_path,
                "context/PLATFORM_CAPABILITY_MATRIX.json",
            ]
            inner_raw = None
            for cand in candidates:
                if cand in inner.namelist():
                    inner_raw = inner.read(cand)
                    break
            if inner_raw is None:
                raise SystemExit(
                    "validator STOP: PLATFORM_CAPABILITY_MATRIX missing from inner ZIP"
                )
            inner_matrix = json.loads(inner_raw.decode("utf-8"))
            assert_matrix_windows_only(inner_matrix, label="inner matrix")
            for key in ("decision_id", "disposition", "supported_platforms"):
                if inner_matrix.get(key) != outer_matrix.get(key):
                    raise SystemExit(
                        f"validator STOP: inner/outer matrix mismatch on {key}"
                    )

        # Scan all text-like members (and nested evidence ZIPs) for forbidden paths.
        for info in zf.infolist():
            if info.is_dir():
                continue
            lower = info.filename.lower()
            data = zf.read(info.filename)
            if lower.endswith(".zip") and info.filename != inner_name:
                with zipfile.ZipFile(zf.open(info.filename)) as nested:
                    for nested_name in nested.namelist():
                        if not nested_name.lower().endswith(
                            (".txt", ".json", ".md", ".log", ".py")
                        ):
                            continue
                        try:
                            nested_text = nested.read(nested_name).decode("utf-8")
                        except UnicodeDecodeError:
                            continue
                        scan_text_for_forbidden_paths(
                            nested_text,
                            label=f"bundle:{info.filename}:{nested_name}",
                        )
                continue
            if not lower.endswith(
                (".txt", ".json", ".md", ".log", ".yaml", ".yml", ".py")
            ):
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            scan_text_for_forbidden_paths(text, label=f"bundle:{info.filename}")

        # Nested inner review ZIP checks.
        with zipfile.ZipFile(zf.open(inner_name)) as inner:
            sums = inner.read("SHA256SUMS").decode("utf-8")
            for line in sums.splitlines():
                line = line.strip()
                if not line:
                    continue
                digest, rel = line.split(None, 1)
                rel = rel.strip()
                actual = hashlib.sha256(inner.read(rel)).hexdigest()
                if actual != digest:
                    raise SystemExit(f"validator STOP: SHA256SUMS mismatch: {rel}")
            manifest = json.loads(inner.read("MANIFEST.json").decode("utf-8"))
            trust = json.loads(inner.read("TRUST_ANCHOR.json").decode("utf-8"))
            if manifest.get("package_digest") != package_digest:
                raise SystemExit("validator STOP: MANIFEST package_digest mismatch")
            if trust.get("package_digest") != package_digest:
                raise SystemExit("validator STOP: TRUST_ANCHOR package_digest mismatch")
            if manifest.get("package_version") != PACKAGE_VERSION:
                raise SystemExit("validator STOP: MANIFEST version mismatch")
            if manifest.get("go_capability") is not False:
                raise SystemExit("validator STOP: MANIFEST go_capability must be false")
            # Full text scan of selected inner docs (includes .py sources).
            # Operator/review docs also get stale current-delivery claim scanning.
            for name in inner.namelist():
                lower = name.lower()
                if not lower.endswith(
                    (".md", ".json", ".txt", ".log", ".yaml", ".yml", ".py")
                ):
                    continue
                try:
                    text = inner.read(name).decode("utf-8")
                except UnicodeDecodeError:
                    continue
                scan_text_for_forbidden_paths(text, label=f"inner:{name}")
                if is_operator_review_document(name, text):
                    scan_text_for_forbidden_claims(
                        text,
                        label=f"inner-operator:{name}",
                        allowed_package_digest=package_digest,
                    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("archive_sha256") != archive_sha:
        raise SystemExit("validator STOP: TEST_REPORT archive_sha256 mismatch")
    if report.get("package_digest") != package_digest:
        raise SystemExit("validator STOP: TEST_REPORT package_digest mismatch")
    if report.get("go_capability") is not False:
        raise SystemExit("validator STOP: TEST_REPORT go_capability must be false")

    # R38: real merge/rebase PREVIEW evidence must ship and bind digests.
    merge_name = f"{PACKAGE_NAME}.MERGE_PREVIEW_EVIDENCE.json"
    rebase_name = f"{PACKAGE_NAME}.REBASE_PREVIEW_EVIDENCE.json"
    index_name = f"{PACKAGE_NAME}.PREVIEW_EVIDENCE_INDEX.json"
    for required in (merge_name, rebase_name, index_name):
        if required not in members:
            raise SystemExit(f"validator STOP: missing bundle member {required}")
    validate_preview_evidence_artifacts(
        merge_path=OUT_DIR / merge_name,
        rebase_path=OUT_DIR / rebase_name,
        package_name=PACKAGE_NAME,
        package_version=PACKAGE_VERSION,
        package_digest=package_digest,
        inner_archive_sha256=archive_sha,
    )
    for name in (merge_name, rebase_name, index_name):
        on_disk = hashlib.sha256((OUT_DIR / name).read_bytes()).hexdigest()
        if members[name]["sha256"] != on_disk:
            raise SystemExit(f"validator STOP: BUNDLE_INDEX hash drift for {name}")
    index_doc = json.loads((OUT_DIR / index_name).read_text(encoding="utf-8"))
    if index_doc.get("package_digest") != package_digest:
        raise SystemExit("validator STOP: PREVIEW_EVIDENCE_INDEX digest mismatch")
    if index_doc.get("inner_archive_sha256") != archive_sha:
        raise SystemExit("validator STOP: PREVIEW_EVIDENCE_INDEX archive mismatch")
    print("POST_BUILD_VALIDATOR_OK")


def write_external_review_request(
    *,
    bundle_sha: str,
    archive_sha: str,
    package_digest: str,
    passed: int,
    skipped: int,
) -> Path:
    """Operator-facing request with filled digests (external; not in inner ZIP)."""
    bundle_display = str(OUT_DIR / f"{PACKAGE_NAME}_REVIEW_BUNDLE.zip")
    text = f"""# EXTERNAL REVIEW REQUEST — `/opsx-resolve-conflict` {REVISION} / {PACKAGE_VERSION}

```text
{bundle_display}
bundle_sha256={bundle_sha}
inner_zip_sha256={archive_sha}
package_digest={package_digest}
clean_unpack={passed} passed, {skipped} skipped
GO_CAPABILITY=false
SAFE_USAGE_SCOPE=PREVIEW_ONLY
native_artifact_root={OUT_DIR}
platform={platform_id()}
```

These digests are external-only. The immutable inner `REVIEW_REQUEST.md` does
not embed them.
"""
    path = OUT_DIR / f"{PACKAGE_NAME}.REVIEW_REQUEST.md"
    path.write_text(text, encoding="utf-8")
    return path


def sync_evidence_placeholders(package_digest: str) -> None:
    """Write digest-consistent evidence without self-referential archive SHA."""
    clean = {
        "schema": "opsx-resolve-conflict/clean-unpack-report/v1",
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "package_digest": package_digest,
        "archive_sha256": None,
        "archive_binding": "external_test_report_only",
        "external_report_path": str(OUT_DIR / f"{PACKAGE_NAME}.TEST_REPORT.json"),
        "raw_log_path": str(OUT_DIR / f"{PACKAGE_NAME}.TEST_REPORT.log"),
        "passed": None,
        "skipped": None,
        "pytest_exit_code": None,
        "author": "Cursor",
        "note": (
            "In-archive archive_sha256 is intentionally null to avoid "
            "self-referential ZIP hash drift. Authoritative archive binding "
            "is the external TEST_REPORT next to the ZIP."
        ),
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
        "go_capability": False,
    }
    index = {
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "author": "Cursor",
        "contract_schema_version": "opsx-resolve-conflict/v2",
        "go_capability": False,
        "safe_usage_scope": "PREVIEW_ONLY",
        "archive": str(OUT_DIR / f"{PACKAGE_NAME}.zip").replace("\\", "\\\\"),
        "archive_sha256": None,
        "archive_binding": "external_test_report_only",
        "package_digest": package_digest,
        "external_test_report": str(
            OUT_DIR / f"{PACKAGE_NAME}.TEST_REPORT.json"
        ).replace("\\", "\\\\"),
        "external_sidecar": str(OUT_DIR / f"{PACKAGE_NAME}.SIDECAR.json").replace(
            "\\", "\\\\"
        ),
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
        "entrypoints": {
            "command": "candidate/.cursor/commands/opsx-resolve-conflict.md",
            "runtime": (
                "candidate/.cursor/opsx-resolve-conflict/runtime/"
                "opsx_conflict/runtime.py"
            ),
            "boot": (
                "candidate/.cursor/opsx-resolve-conflict/runtime/"
                "boot_opsx_conflict.py"
            ),
        },
        "review_docs": [
            "00_SCOPE.md",
            "01_REVIEW_STANDARD.md",
            "02_REQUIRED_CONTEXT.md",
            "03_VERDICT_SCHEMA.md",
            "04_REVISION_CLOSURE_MATRIX.md",
            "AUTHORSHIP.md",
            "CHANGELOG.md",
            "REVIEW_REQUEST.md",
            "README_REVIEW.md",
            "TRUST_ANCHOR.json",
            "context/OPSX_CONTEXT_EXTRACT.md",
            "context/host_contracts/",
            "context/HOST_CONTRACT_HASHES.json",
            "context/SOURCE_LINEAGE.json",
        ],
        "supersedes_rejected": [
            "0.5.0",
            "0.6.0",
            "0.7.0",
            "0.8.0",
            "0.9.0",
            "0.10.0",
            "0.11.0",
            "0.12.0",
            "0.13.0",
            "0.14.0",
            "0.15.0",
            "0.16.0",
            "0.17.0",
            "0.18.0",
            "0.19.0",
            "0.20.0",
        ],
    }
    _write_json(PACKAGE_ROOT / "CLEAN_UNPACK_TEST_REPORT.json", clean)
    _write_json(PACKAGE_ROOT / "PACKAGE_INDEX.json", index)


def build_archive() -> tuple[Path, str, str]:
    """Build review ZIP once; return (zip_path, archive_sha256, package_digest)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = str(PACKAGE_ROOT / "runtime")
    scripts = PACKAGE_ROOT / "scripts"
    write_inner_review_request()
    restore_host_contracts_from_origin()
    subprocess.check_call(
        [sys.executable, str(scripts / "update_manifest_hashes.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    subprocess.check_call(
        [sys.executable, str(scripts / "build_lineage_mapping.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    # Lineage persists origin/snapshot fields onto MANIFEST; refresh digests
    # before replay so OPSX_CONFLICT_TRUST_DIGEST matches package_compatibility_gate.
    subprocess.check_call(
        [sys.executable, str(scripts / "update_manifest_hashes.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    subprocess.check_call(
        [sys.executable, str(scripts / "build_replay_evidence.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_digest = manifest["package_digest"]
    sync_evidence_placeholders(package_digest)
    # Final digest refresh after evidence placeholders (placeholders excluded
    # from digest inputs by design in update_manifest_hashes inventory policy).
    subprocess.check_call(
        [sys.executable, str(scripts / "update_manifest_hashes.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_digest = manifest["package_digest"]
    sync_evidence_placeholders(package_digest)
    subprocess.check_call(
        [sys.executable, str(scripts / "build_review_archive.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    zip_path = OUT_DIR / f"{PACKAGE_NAME}.zip"
    archive_sha = sha256_file(zip_path)
    # Re-read digest after build (build refreshes host hashes / installed cmd).
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_digest = manifest["package_digest"]
    # Do NOT rebuild ZIP after this point — placeholders already baked in.
    # If digest drifted because build wrote MANIFEST into ZIP from a second
    # pass historically, re-sync placeholders and rebuild exactly once here,
    # then freeze.
    sync_evidence_placeholders(package_digest)
    subprocess.check_call(
        [sys.executable, str(scripts / "update_manifest_hashes.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_digest = manifest["package_digest"]
    sync_evidence_placeholders(package_digest)
    subprocess.check_call(
        [sys.executable, str(scripts / "build_review_archive.py")],
        cwd=str(PACKAGE_ROOT),
        env=env,
    )
    archive_sha = sha256_file(zip_path)
    manifest = json.loads((PACKAGE_ROOT / "MANIFEST.json").read_text(encoding="utf-8"))
    package_digest = manifest["package_digest"]
    return zip_path, archive_sha, package_digest


def verify_zip_internal_consistency(zip_path: Path, package_digest: str) -> None:
    """Fail closed if delivered ZIP contains digest/archive drift."""
    with zipfile.ZipFile(zip_path) as zf:
        for name in (
            "MANIFEST.json",
            "TRUST_ANCHOR.json",
            "CLEAN_UNPACK_TEST_REPORT.json",
            "PACKAGE_INDEX.json",
            "candidate/.cursor/opsx-resolve-conflict/MANIFEST.json",
            "candidate/.cursor/opsx-resolve-conflict/CLEAN_UNPACK_TEST_REPORT.json",
            "candidate/.cursor/opsx-resolve-conflict/PACKAGE_INDEX.json",
        ):
            payload = json.loads(zf.read(name))
            digest = payload.get("package_digest")
            if digest != package_digest:
                raise SystemExit(
                    f"ZIP digest drift in {name}: {digest} != {package_digest}"
                )
            if "archive_sha256" in payload and payload.get("archive_sha256") not in (
                None,
                "",
            ):
                raise SystemExit(
                    f"ZIP {name} must not embed archive_sha256 "
                    f"(got {payload.get('archive_sha256')})"
                )


def run_clean_unpack(zip_path: Path) -> tuple[int, int, int, Path, str]:
    """Extract ZIP and run package pytest; return passed/skipped/exit/log/raw_sha."""
    unpack = OUT_DIR / f"OPSX_{REVISION}_CLEAN_UNPACK"
    shutil.rmtree(unpack, ignore_errors=True)
    unpack.mkdir(parents=True)
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(unpack)
    wd = unpack / "candidate" / ".cursor" / "opsx-resolve-conflict"
    env = dict(os.environ)
    env["PYTHONPATH"] = "runtime"
    python_dir = str(Path(sys.executable).resolve().parent)
    git_exe = shutil.which("git")
    path_parts = [python_dir]
    if git_exe:
        path_parts.append(str(Path(git_exe).resolve().parent))
    if os.name == "nt":
        windir = env.get("WINDIR", r"C:\Windows")
        path_parts.append(str(Path(windir) / "System32"))
    env["PATH"] = os.pathsep.join(path_parts)
    env.pop("VIRTUAL_ENV", None)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests",
            "-q",
            "-ra",
            "--confcutdir=tests",
        ],
        cwd=str(wd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    raw = proc.stdout + proc.stderr
    raw_bytes = raw.encode("utf-8")
    log_path = OUT_DIR / f"{PACKAGE_NAME}.TEST_REPORT.log"
    # Binary write avoids Windows newline translation drifting raw_log_sha256.
    log_path.write_bytes(raw_bytes)
    legacy = OUT_DIR / f"OPSX_{REVISION}_FINAL_CLEAN_UNPACK_pytest.log"
    legacy.write_bytes(raw_bytes)
    raw_log_sha = hashlib.sha256(raw_bytes).hexdigest()
    passed = skipped = 0
    m = re.search(r"(\d+) passed(?:, (\d+) skipped)?", raw)
    if m:
        passed = int(m.group(1))
        skipped = int(m.group(2) or "0")
    skip_rows: list[dict[str, str]] = []
    for line in raw.splitlines():
        # pytest -ra short summary: SKIPPED [1] tests/foo.py:12: reason
        sm = re.match(
            r"SKIPPED\s+\[\d+\]\s+(.+?):(\d+):\s*(.*)$",
            line.strip(),
        )
        if not sm:
            continue
        node = sm.group(1).replace("\\", "/")
        lineno = sm.group(2)
        reason = (sm.group(3) or "").strip() or "unspecified"
        platform_skip = any(
            token in reason.lower()
            for token in ("win", "windows", "posix", "linux", "darwin", "symlink")
        )
        skip_rows.append(
            {
                "nodeid": f"{node}::{lineno}",
                "path": node,
                "lineno": lineno,
                "reason": reason,
                "platform": sys.platform,
                "classification": "non_mandatory" if platform_skip else "review",
                "mandatory": "false" if platform_skip else "true",
                "basis": (
                    "platform-dependent fixture capability"
                    if platform_skip
                    else "requires explicit non-mandatory justification"
                ),
            }
        )
    skip_inventory = {
        "schema": "opsx-resolve-conflict/skip-inventory/v1",
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "passed": passed,
        "skipped": skipped,
        "rows": skip_rows,
        "note": (
            "Machine-readable skip inventory from pytest -ra. "
            "mandatory=true rows require review justification."
        ),
    }
    skip_path = OUT_DIR / f"{PACKAGE_NAME}.SKIP_INVENTORY.json"
    _write_json(skip_path, skip_inventory)
    (wd / "context" / "SKIP_INVENTORY.json").parent.mkdir(parents=True, exist_ok=True)
    # Mirror into package tree for next archive rebuild is not done here —
    # inventory is external evidence next to TEST_REPORT.
    (PACKAGE_ROOT / "context" / "SKIP_INVENTORY.json").write_text(
        json.dumps(skip_inventory, indent=2) + "\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print(raw)
        raise SystemExit(f"clean-unpack pytest failed: exit={proc.returncode}")
    # Fail closed if any skip is classified mandatory without basis.
    for row in skip_rows:
        if row.get("mandatory") == "true" and "unspecified" in row.get("reason", ""):
            raise SystemExit(f"clean-unpack mandatory skip unexplained: {row}")
    return passed, skipped, proc.returncode, log_path, raw_log_sha


def write_external_artifacts(
    *,
    package_digest: str,
    archive_sha: str,
    passed: int,
    skipped: int,
    exit_code: int,
    built_at: str,
    raw_log_sha: str,
    log_path: Path,
) -> tuple[Path, Path]:
    """Write TEST_REPORT.json + SIDECAR.json bound to delivered ZIP."""
    report = {
        "schema": "opsx-resolve-conflict/external-test-report/v1",
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "package_digest": package_digest,
        "archive_path": str(OUT_DIR / f"{PACKAGE_NAME}.zip"),
        "archive_sha256": archive_sha,
        "archive_binding": "external_test_report_only",
        "raw_log_path": str(log_path),
        "raw_log_sha256": raw_log_sha,
        "pytest_summary": {
            "passed": passed,
            "skipped": skipped,
            "failed": 0,
            "exit_code": exit_code,
        },
        "host_poetry_required_for_clean_unpack": False,
        "go_capability": False,
        "safe_usage_scope": "PREVIEW_ONLY",
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
        "commands": [
            "python scripts/ship_review_package.py",
            "pytest tests -q -ra --confcutdir=tests",
        ],
        "skip_inventory_path": str(OUT_DIR / f"{PACKAGE_NAME}.SKIP_INVENTORY.json"),
        "author": "Cursor",
        "built_at_utc": built_at,
    }
    report_path = OUT_DIR / f"{PACKAGE_NAME}.TEST_REPORT.json"
    _write_json(report_path, report)

    sidecar = {
        "schema": "opsx-resolve-conflict/ship-sidecar/v1",
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "package_digest": package_digest,
        "archive_sha256": archive_sha,
        "raw_log_sha256": raw_log_sha,
        "artifacts": {
            "zip": str(OUT_DIR / f"{PACKAGE_NAME}.zip"),
            "test_report_json": str(report_path),
            "test_report_log": str(log_path),
            "sidecar": str(OUT_DIR / f"{PACKAGE_NAME}.SIDECAR.json"),
            "skip_inventory": str(OUT_DIR / f"{PACKAGE_NAME}.SKIP_INVENTORY.json"),
            "replay_evidence": str(OUT_DIR / f"{PACKAGE_NAME}.REPLAY_EVIDENCE.zip"),
            "merge_preview_evidence": str(
                OUT_DIR / f"{PACKAGE_NAME}.MERGE_PREVIEW_EVIDENCE.json"
            ),
            "rebase_preview_evidence": str(
                OUT_DIR / f"{PACKAGE_NAME}.REBASE_PREVIEW_EVIDENCE.json"
            ),
            "preview_evidence_index": str(
                OUT_DIR / f"{PACKAGE_NAME}.PREVIEW_EVIDENCE_INDEX.json"
            ),
            "lineage": "context/SOURCE_LINEAGE.json",
        },
        "post_test_zip_immutable": True,
        "go_capability": False,
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
        "built_at_utc": built_at,
        "author": "Cursor",
    }
    sidecar_path = OUT_DIR / f"{PACKAGE_NAME}.SIDECAR.json"
    _write_json(sidecar_path, sidecar)

    # Local post-ship mirror: keep digest match; leave archive_sha256 null.
    clean = json.loads(
        (PACKAGE_ROOT / "CLEAN_UNPACK_TEST_REPORT.json").read_text(encoding="utf-8")
    )
    clean.update(
        {
            "package_digest": package_digest,
            "passed": passed,
            "skipped": skipped,
            "pytest_exit_code": exit_code,
            "archive_sha256": None,
            "archive_binding": "external_test_report_only",
            "external_archive_sha256_ref": archive_sha,
            "raw_log_sha256_ref": raw_log_sha,
        }
    )
    index = json.loads((PACKAGE_ROOT / "PACKAGE_INDEX.json").read_text(encoding="utf-8"))
    index.update(
        {
            "package_digest": package_digest,
            "archive_sha256": None,
            "archive_binding": "external_test_report_only",
            "external_archive_sha256_ref": archive_sha,
            "raw_log_sha256_ref": raw_log_sha,
        }
    )
    _write_json(PACKAGE_ROOT / "CLEAN_UNPACK_TEST_REPORT.json", clean)
    _write_json(PACKAGE_ROOT / "PACKAGE_INDEX.json", index)
    return report_path, sidecar_path


def build_review_bundle(
    *,
    package_digest: str,
    archive_sha: str,
    report_path: Path,
    sidecar_path: Path,
    log_path: Path,
    built_at: str,
) -> tuple[Path, str]:
    """Pack review ZIP + external evidence into one delivery archive.

    The inner review ZIP stays immutable; this wrapper is the single file to
    hand to independent review.
    """
    members = [
        OUT_DIR / f"{PACKAGE_NAME}.zip",
        report_path,
        log_path,
        sidecar_path,
        OUT_DIR / f"{PACKAGE_NAME}.SKIP_INVENTORY.json",
        OUT_DIR / f"{PACKAGE_NAME}.REPLAY_EVIDENCE.zip",
        OUT_DIR / f"{PACKAGE_NAME}.MERGE_PREVIEW_EVIDENCE.json",
        OUT_DIR / f"{PACKAGE_NAME}.REBASE_PREVIEW_EVIDENCE.json",
        OUT_DIR / f"{PACKAGE_NAME}.PREVIEW_EVIDENCE_INDEX.json",
        OUT_DIR / f"{PACKAGE_NAME}.AUTHOR.txt",
        OUT_DIR / f"{PACKAGE_NAME}.PLATFORM_CAPABILITY_MATRIX.json",
    ]
    missing = [str(p) for p in members if not p.is_file()]
    if missing:
        raise SystemExit(f"review bundle missing members: {missing}")
    bundle_path = OUT_DIR / f"{PACKAGE_NAME}_REVIEW_BUNDLE.zip"
    if bundle_path.exists():
        bundle_path.unlink()
    index = {
        "schema": "opsx-resolve-conflict/review-bundle/v1",
        "package_name": PACKAGE_NAME,
        "package_version": PACKAGE_VERSION,
        "built_at_utc": built_at,
        "author": "Cursor",
        "inner_review_zip": f"{PACKAGE_NAME}.zip",
        "inner_archive_sha256": archive_sha,
        "package_digest": package_digest,
        "go_capability": False,
        "open_blockers": [
            "BLOCKER_AUTHORITY_PRODUCER_MISSING",
            "BLOCKER_OS_SANDBOX_RUNNER_MISSING",
        ],
        "note": (
            "Single delivery archive for independent review. Inner review ZIP "
            "is immutable; TEST_REPORT/SIDECAR bind its archive_sha256."
        ),
        "members": [],
    }
    with zipfile.ZipFile(bundle_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in members:
            digest = sha256_file(path)
            zf.write(path, path.name)
            index["members"].append(
                {
                    "path": path.name,
                    "sha256": digest,
                    "bytes": path.stat().st_size,
                }
            )
        zf.writestr("BUNDLE_INDEX.json", json.dumps(index, indent=2) + "\n")
    return bundle_path, sha256_file(bundle_path)


def main() -> None:
    """Ship R33 archive with digest-consistent external evidence."""
    built_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Freeze ADR platform policy into the immutable package tree before ZIP.
    write_immutable_platform_matrix()
    zip_path, archive_sha, package_digest = build_archive()
    verify_zip_internal_consistency(zip_path, package_digest)
    frozen_sha = sha256_file(zip_path)
    if frozen_sha != archive_sha:
        raise SystemExit("ZIP hash unstable immediately after build")
    passed, skipped, exit_code, log_path, raw_log_sha = run_clean_unpack(zip_path)
    if sha256_file(zip_path) != frozen_sha:
        raise SystemExit("ZIP mutated during clean-unpack tests")
    report, sidecar = write_external_artifacts(
        package_digest=package_digest,
        archive_sha=frozen_sha,
        passed=passed,
        skipped=skipped,
        exit_code=exit_code,
        built_at=built_at,
        raw_log_sha=raw_log_sha,
        log_path=log_path,
    )
    if sha256_file(zip_path) != frozen_sha:
        raise SystemExit("ZIP mutated after evidence binding")
    host_report = {
        "platform": platform_id(),
        "passed": passed,
        "skipped": skipped,
        "pytest_exit_code": exit_code,
        "archive_sha256": frozen_sha,
        "package_digest": package_digest,
        "test_report": str(report),
        "native_artifact_root": str(OUT_DIR),
    }
    windows_report = host_report if platform_id() == "windows" else None
    # ADR: do not attempt Linux enablement evidence; linux/macos are UNSUPPORTED.
    write_external_platform_matrix(windows_report=windows_report)
    # R38: real merge/rebase PREVIEW evidence from packaged ZIP runtime.
    build_preview_evidence_for_ship(
        archive_path=zip_path,
        out_dir=OUT_DIR,
        package_name=PACKAGE_NAME,
        package_version=PACKAGE_VERSION,
        package_digest=package_digest,
        inner_archive_sha256=frozen_sha,
    )
    if sha256_file(zip_path) != frozen_sha:
        raise SystemExit("ZIP mutated during preview evidence generation")
    bundle_path, bundle_sha = build_review_bundle(
        package_digest=package_digest,
        archive_sha=frozen_sha,
        report_path=report,
        sidecar_path=sidecar,
        log_path=log_path,
        built_at=built_at,
    )
    validate_review_bundle(
        bundle_path=bundle_path,
        package_digest=package_digest,
        archive_sha=frozen_sha,
        report_path=report,
    )
    external_req = write_external_review_request(
        bundle_sha=bundle_sha,
        archive_sha=frozen_sha,
        package_digest=package_digest,
        passed=passed,
        skipped=skipped,
    )
    print(f"SHIP_OK package={PACKAGE_NAME} version={PACKAGE_VERSION}")
    print(f"review_bundle={bundle_path}")
    print(f"review_bundle_sha256={bundle_sha}")
    print(f"archive={zip_path}")
    print(f"archive_sha256={frozen_sha}")
    print(f"package_digest={package_digest}")
    print(f"external_report={report}")
    print(f"sidecar={sidecar}")
    print(f"external_review_request={external_req}")
    print(f"raw_log={log_path}")
    print(f"raw_log_sha256={raw_log_sha}")
    print(f"pytest passed={passed} skipped={skipped} exit={exit_code}")


if __name__ == "__main__":
    main()
