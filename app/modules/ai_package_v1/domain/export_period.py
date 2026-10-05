"""Период экспорта (календарные даты)."""

from datetime import date

from pydantic import BaseModel


class ExportPeriod(BaseModel):
    """Календарный период экспорта (включительно)."""

    start: date
    end: date

    def to_manifest_dict(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}
