"""Portable, contract-first wrapper for the canonical read-only collector.

The legacy ``run.py`` surface remains compatible for existing operators. This
module adds a CWD-independent contract with explicit client, period, run ID,
output directory, and shop ID. It delegates collection to the existing
generic WB/API/DB adapters and only adds run isolation, provenance, coverage,
and an integrity gate around their output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

_COLLECT_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_REPOSITORY_ROOT = _COLLECT_PACKAGE_ROOT.parent
for _path in (str(_REPOSITORY_ROOT), str(_COLLECT_PACKAGE_ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
PERIOD_RE = re.compile(
    r"^(?P<start>\d{4}-\d{2}-\d{2})\.\.(?P<end>\d{4}-\d{2}-\d{2})$"
)
REQUIRED_CREDENTIALS = ("POSTGRES_USER", "POSTGRES_PASSWORD")
MANIFEST_NAME = "manifest.json"
INTEGRITY_NAME = "integrity.json"
PROVENANCE_NAME = "provenance.json"


class ContractError(ValueError):
    """Invalid portable collector contract."""


class CredentialsUnavailableError(RuntimeError):
    """Required credentials are not present in the selected environment."""


class OutputAlreadyClaimedError(FileExistsError):
    """The requested output directory is already owned by another run."""


@dataclass(frozen=True)
class CollectionContract:
    """Validated, explicit input contract for one isolated collection run."""

    client: str
    period_start: date
    period_end: date
    run_id: str
    output_dir: Path
    shop_id: str
    closed_through: date

    @property
    def period(self) -> str:
        """Return the canonical inclusive period string."""
        return f"{self.period_start.isoformat()}..{self.period_end.isoformat()}"


def parse_period(value: str) -> tuple[date, date]:
    """Parse an inclusive ``YYYY-MM-DD..YYYY-MM-DD`` period."""
    match = PERIOD_RE.fullmatch(value.strip())
    if match is None:
        raise ContractError("period must be YYYY-MM-DD..YYYY-MM-DD")
    try:
        start = date.fromisoformat(match.group("start"))
        end = date.fromisoformat(match.group("end"))
    except ValueError as exc:
        raise ContractError("period contains an invalid calendar date") from exc
    if end < start:
        raise ContractError("period end must not precede period start")
    return start, end


def validate_safe_name(value: str, field: str) -> str:
    """Validate a path-component contract field against traversal."""
    if SAFE_NAME.fullmatch(value) is None:
        raise ContractError(f"{field} must be a safe single path component")
    return value


def current_closed_through() -> date:
    """Return yesterday in the contract timezone as the closed-day boundary."""
    return (datetime.now(ZoneInfo("Europe/Moscow")) - timedelta(days=1)).date()


def build_contract(args: argparse.Namespace) -> CollectionContract:
    """Build and validate the explicit portable contract from CLI arguments."""
    start, end = parse_period(args.period)
    try:
        closed_through = (
            date.fromisoformat(args.closed_through)
            if args.closed_through
            else current_closed_through()
        )
    except ValueError as exc:
        raise ContractError("closed-through must be YYYY-MM-DD") from exc
    if not args.shop_id.strip():
        raise ContractError("shop-id must not be empty")
    return CollectionContract(
        client=validate_safe_name(args.client, "client"),
        period_start=start,
        period_end=end,
        run_id=validate_safe_name(args.run_id, "run-id"),
        output_dir=Path(args.output_dir).expanduser().resolve(),
        shop_id=args.shop_id.strip(),
        closed_through=closed_through,
    )


def credential_presence(
    environ: Mapping[str, str] | None = None,
) -> dict[str, bool]:
    """Return credential presence only; never return credential values."""
    source = environ if environ is not None else os.environ
    return {key: bool(source.get(key, "").strip()) for key in REQUIRED_CREDENTIALS}


def require_credentials(environ: Mapping[str, str] | None = None) -> None:
    """Fail closed when the minimum DB credential contract is unavailable."""
    presence = credential_presence(environ)
    missing = [key for key, present in presence.items() if not present]
    if missing:
        raise CredentialsUnavailableError(
            "missing required credentials: " + ", ".join(missing)
        )


def classify_days(
    period_start: date,
    period_end: date,
    *,
    closed_through: date,
) -> list[dict[str, str]]:
    """Classify every requested day without assigning missing data to zero."""
    rows: list[dict[str, str]] = []
    day = period_start
    while day <= period_end:
        state = "CLOSED" if day <= closed_through else "OPEN"
        rows.append(
            {
                "date": day.isoformat(),
                "day_state": state,
                "evidence_status": "NOT_INFERRED_FROM_ABSENCE",
            }
        )
        day += timedelta(days=1)
    return rows


def claim_output_dir(path: Path) -> Path:
    """Atomically claim an empty run directory; never merge concurrent runs."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.mkdir()
    except FileExistsError as exc:
        raise OutputAlreadyClaimedError(str(path)) from exc
    return path


def redact_command(command: Sequence[str]) -> list[str]:
    """Redact secret-like CLI values and repository absolute paths."""
    redacted: list[str] = []
    hide_next = False
    for item in command:
        if hide_next:
            redacted.append("<redacted>")
            hide_next = False
            continue
        normalized = item.lower()
        if any(term in normalized for term in ("token", "password", "secret", "api-key")):
            if "=" in item:
                redacted.append(item.split("=", 1)[0] + "=<redacted>")
            else:
                redacted.append(item)
                hide_next = True
            continue
        redacted.append(Path(item).name if Path(item).is_absolute() else item)
    return redacted


def _redact_text(value: str) -> str:
    """Remove obvious credential-bearing values from captured process logs."""
    return re.sub(
        r"(?i)(authorization\s*:\s*bearer|password|token|secret|api[_-]?key)\s*[=:]\s*\S+",
        r"\1=<redacted>",
        value,
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json_read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def validate_integrity(root: Path) -> dict[str, Any]:
    """Validate every file hash declared by the portable manifest."""
    manifest = _json_read(root / MANIFEST_NAME)
    failures: list[str] = []
    checked = 0
    for item in manifest.get("files", []):
        if not isinstance(item, dict):
            failures.append("manifest.files contains a non-object")
            continue
        relative = str(item.get("path") or "")
        expected = str(item.get("sha256") or "")
        candidate = (root / relative).resolve()
        if root not in candidate.parents:
            failures.append(f"path escapes output: {relative}")
            continue
        if not candidate.is_file():
            failures.append(f"missing: {relative}")
            continue
        checked += 1
        actual = _sha256(candidate)
        if actual != expected:
            failures.append(f"hash mismatch: {relative}")
    return {"pass": not failures, "checked_files": checked, "failures": failures}


def _write_portable_metadata(
    contract: CollectionContract,
    *,
    command: Sequence[str],
    collector_returncode: int,
    collector_stdout: str,
    collector_stderr: str,
) -> dict[str, Any]:
    """Write provenance/manifest/integrity metadata after legacy collection."""
    root = contract.output_dir
    (root / "collector.stdout.log").write_text(
        _redact_text(collector_stdout), encoding="utf-8"
    )
    (root / "collector.stderr.log").write_text(
        _redact_text(collector_stderr), encoding="utf-8"
    )
    legacy_report = _json_read(root / "report.json")
    coverage = legacy_report.get("coverage", [])
    gaps = list(legacy_report.get("integrity", {}).get("errors", []))
    gaps.extend(legacy_report.get("missing_collector_capabilities", []))
    checked_at = datetime.now(timezone.utc).isoformat()
    provenance = {
        "source": [
            "Wildberries read-only API through existing generic adapters",
            "PostgreSQL read-only identity/access path through existing stack",
        ],
        "shop_id": contract.shop_id,
        "checked_at": checked_at,
        "credentials_present": credential_presence(),
        "business_writes": 0,
        "db_writes": 0,
        "mode": "STRICT_READ_ONLY",
    }
    (root / PROVENANCE_NAME).write_text(
        json.dumps(provenance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    files: list[dict[str, Any]] = []
    excluded = {MANIFEST_NAME, INTEGRITY_NAME}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name in excluded:
            continue
        relative = path.relative_to(root).as_posix()
        files.append(
            {"path": relative, "size": path.stat().st_size, "sha256": _sha256(path)}
        )
    manifest = {
        "schema_version": "wb-readonly-portable-v1",
        "client": contract.client,
        "period": contract.period,
        "period_start": contract.period_start.isoformat(),
        "period_end": contract.period_end.isoformat(),
        "closed_through": contract.closed_through.isoformat(),
        "run_id": contract.run_id,
        "shop_id": contract.shop_id,
        "checked_at": checked_at,
        "command": redact_command(command),
        "mode": "STRICT_READ_ONLY",
        "collector_returncode": collector_returncode,
        "coverage": coverage,
        "day_boundaries": classify_days(
            contract.period_start,
            contract.period_end,
            closed_through=contract.closed_through,
        ),
        "gaps": gaps,
        "provenance": PROVENANCE_NAME,
        "business_writes": 0,
        "db_writes": 0,
        "files": files,
    }
    (root / MANIFEST_NAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    gate = validate_integrity(root)
    integrity = {
        **gate,
        "manifest_sha256": _sha256(root / MANIFEST_NAME),
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    (root / INTEGRITY_NAME).write_text(
        json.dumps(integrity, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {"manifest": manifest, "integrity": integrity}


def build_legacy_command(
    contract: CollectionContract, args: argparse.Namespace
) -> list[str]:
    """Build the compatibility command; collect mode is fixed and write-free."""
    run_path = Path(__file__).resolve().parents[1] / "run.py"
    return [
        sys.executable,
        str(run_path),
        "--shop-id",
        contract.shop_id,
        "--mode",
        "collect",
        "--orders-date-from",
        contract.period_start.isoformat(),
        "--ads-date-from",
        contract.period_start.isoformat(),
        "--ads-date-to",
        contract.period_end.isoformat(),
        "--max-seconds",
        str(args.max_seconds),
        "--max-api-calls",
        str(args.max_api_calls),
        "--output-dir",
        str(contract.output_dir),
    ]


def run_collection(contract: CollectionContract, args: argparse.Namespace) -> dict[str, Any]:
    """Run one isolated, read-only collection and return verified metadata."""
    require_credentials()
    claim_output_dir(contract.output_dir)
    command = build_legacy_command(contract, args)
    completed = subprocess.run(
        command,
        cwd=_REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    metadata = _write_portable_metadata(
        contract,
        command=command,
        collector_returncode=completed.returncode,
        collector_stdout=completed.stdout,
        collector_stderr=completed.stderr,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"legacy collector failed with return code {completed.returncode}"
        )
    return metadata


def build_parser() -> argparse.ArgumentParser:
    """Build the explicit portable CLI contract."""
    parser = argparse.ArgumentParser(
        prog="wb-api-readonly-collect",
        description="Canonical portable STRICT_READ_ONLY WB collector",
    )
    parser.add_argument("--client", required=True)
    parser.add_argument("--period", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--shop-id", required=True)
    parser.add_argument("--closed-through", default=None)
    parser.add_argument("--env-file", default=None)
    parser.add_argument("--max-seconds", type=float, default=3600.0)
    parser.add_argument("--max-api-calls", type=int, default=10000)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Validate the contract and credentials without contacting sources",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the portable collector and return a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        if args.env_file:
            load_dotenv(Path(args.env_file).expanduser(), override=False)
        else:
            load_dotenv(_REPOSITORY_ROOT / ".env", override=False)
        contract = build_contract(args)
        require_credentials()
        if args.preflight_only:
            print(
                json.dumps(
                    {
                        "status": "PREFLIGHT_OK",
                        "client": contract.client,
                        "period": contract.period,
                        "run_id": contract.run_id,
                        "output_dir": str(contract.output_dir),
                        "mode": "STRICT_READ_ONLY",
                        "credentials_present": credential_presence(),
                    },
                    ensure_ascii=False,
                )
            )
            return 0
        metadata = run_collection(contract, args)
        print(json.dumps(metadata["integrity"], ensure_ascii=False, indent=2))
        return 0 if metadata["integrity"]["pass"] else 1
    except (ContractError, CredentialsUnavailableError, OutputAlreadyClaimedError) as exc:
        print(f"portable collector blocked: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - CLI must return a stable failure
        print(f"portable collector failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
