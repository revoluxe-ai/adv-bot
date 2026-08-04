"""Owner-local L0 archive: payload + report + sha256 (secret-strip only)."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
from typing import Any

from scripts.wb_api_readonly_ops.models import RunReport
from scripts.wb_api_readonly_ops.secret_strip import strip_secrets

DEFAULT_OUTPUT_DIR = Path("scripts/wb_api_readonly_ops/outputs")
ARCHIVE_NAME = "wb_readonly_research.zip"
REPORT_NAME = "report.json"
PAYLOAD_NAME = "payload.json"
SHA256_NAME = "archive.sha256"


def write_l0_archive(
    report: RunReport,
    *,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    """Записать zip (report+payload) после secret-strip; вернуть (path, sha256 hex)."""
    out = output_dir or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    archive_path = out / ARCHIVE_NAME

    safe_report = strip_secrets(report.to_dict())
    payload: dict[str, Any] = {
        "families": {
            fr.family.value: strip_secrets(fr.payload) for fr in report.families
        }
    }

    report_bytes = json.dumps(safe_report, ensure_ascii=False, indent=2).encode("utf-8")
    payload_bytes = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")

    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(REPORT_NAME, report_bytes)
        zf.writestr(PAYLOAD_NAME, payload_bytes)

    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    (out / SHA256_NAME).write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="utf-8")
    # Loose report for kubectl cp convenience / opsx-scripts known outputs
    (out / REPORT_NAME).write_bytes(report_bytes)
    return archive_path, digest
