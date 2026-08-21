"""JSONL raw store + artifact integrity gate."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.wb_api_readonly_ops.collect.coverage import ArtifactIntegrityError, CoverageEntry
from scripts.wb_api_readonly_ops.secret_strip import strip_secrets


@dataclass
class RawStore:
    """Пишет raw datasets в JSONL под output_dir/raw/."""

    output_dir: Path
    coverage: list[CoverageEntry] = field(default_factory=list)
    _paths: dict[str, Path] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "raw").mkdir(parents=True, exist_ok=True)

    @property
    def raw_root(self) -> Path:
        return self.output_dir / "raw"

    def path_for(self, relative: str) -> Path:
        """Absolute path для raw/relative (создаёт parent dirs)."""
        rel = relative.replace("\\", "/").lstrip("/")
        path = self.raw_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        self._paths[rel] = path
        return path

    def write_jsonl(
        self,
        relative: str,
        rows: list[dict[str, Any]],
        *,
        entry: CoverageEntry,
    ) -> Path:
        """Записать все rows в JSONL; обновить coverage и integrity gate."""
        path = self.path_for(relative)
        entry.records_fetched = len(rows)
        stored = 0
        with path.open("w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                safe = strip_secrets(row)
                if not isinstance(safe, dict):
                    safe = {"value": safe}
                fh.write(json.dumps(safe, ensure_ascii=False) + "\n")
                stored += 1
        entry.records_stored = stored
        entry.assert_integrity()
        self.coverage.append(entry)
        return path

    def write_json(
        self,
        relative: str,
        payload: object,
        *,
        entry: CoverageEntry,
        records_count: int | None = None,
    ) -> Path:
        """Записать один JSON document (например campaign_ids)."""
        path = self.path_for(relative)
        safe = strip_secrets(payload)
        path.write_text(
            json.dumps(safe, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        count = records_count if records_count is not None else (
            len(payload) if isinstance(payload, list) else 1
        )
        entry.records_fetched = count
        entry.records_stored = count
        entry.assert_integrity()
        self.coverage.append(entry)
        return path

    def finalize_integrity(self) -> None:
        """Проверить все coverage entries на fetched==stored."""
        for entry in self.coverage:
            entry.assert_integrity()

    def manifest_paths(self) -> dict[str, str]:
        """Относительные пути raw файлов для manifest.json."""
        return {key: f"raw/{key}" for key in sorted(self._paths)}
