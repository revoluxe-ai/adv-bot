"""Collect v2 ZIP: report.json + manifest.json + raw/*.jsonl."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.wb_api_readonly_ops.archive import ARCHIVE_NAME, DEFAULT_OUTPUT_DIR
from scripts.wb_api_readonly_ops.collect.coverage import CoverageEntry
from scripts.wb_api_readonly_ops.secret_strip import strip_secrets

COLLECT_LAYOUT_VERSION = "collect_v2"


@dataclass
class CollectReport:
    """Coverage-first report для full collect (без inline raw payload)."""

    shop_id: str
    overall_status: str
    coverage: list[CoverageEntry]
    integrity_pass: bool
    integrity_errors: list[str]
    api_budget: dict[str, Any]
    artifact_layout: str = COLLECT_LAYOUT_VERSION
    label: str = "owner_local_collect"
    archive_sha256: str | None = None
    missing_capabilities: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return strip_secrets(
            {
                "label": self.label,
                "mode": "collect",
                "shop_id": self.shop_id,
                "overall_status": self.overall_status,
                "artifact_layout": self.artifact_layout,
                "coverage": [c.to_dict() for c in self.coverage],
                "integrity": {
                    "pass": self.integrity_pass,
                    "errors": self.integrity_errors,
                },
                "api_budget": self.api_budget,
                "archive_sha256": self.archive_sha256,
                "missing_collector_capabilities": self.missing_capabilities or [],
                "web_pass_claimed": False,
                "note": (
                    "Full READ_ONLY collect (JSONL raw store). "
                    "NOT Web READ_ONLY_PREFLIGHT_PASS / CLEAN_DUMP."
                ),
            }
        )


def write_collect_archive(
    report: CollectReport,
    *,
    staging_dir: Path,
    output_dir: Path | None = None,
) -> tuple[Path, str]:
    """Упаковать staging_dir (raw/ + report) в wb_readonly_research.zip."""
    out = output_dir or DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)
    report_path = staging_dir / "report.json"
    manifest_path = staging_dir / "manifest.json"
    manifest = {
        "layout": COLLECT_LAYOUT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "shop_id": report.shop_id,
        "files": _list_staging_files(staging_dir),
    }
    manifest_path.write_text(
        json.dumps(strip_secrets(manifest), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    archive_path = out / ARCHIVE_NAME
    with zipfile.ZipFile(
        archive_path, "w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        for path in sorted(staging_dir.rglob("*")):
            if path.is_file():
                arcname = path.relative_to(staging_dir).as_posix()
                zf.write(path, arcname=arcname)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    sidecar = out / "archive.sha256"
    sidecar.write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="utf-8")
    loose_report = out / "report.json"
    loose_report.write_text(
        json.dumps(
            {**report.to_dict(), "archive_sha256": digest},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return archive_path, digest


def _list_staging_files(staging_dir: Path) -> list[str]:
    return sorted(
        p.relative_to(staging_dir).as_posix()
        for p in staging_dir.rglob("*")
        if p.is_file()
    )
