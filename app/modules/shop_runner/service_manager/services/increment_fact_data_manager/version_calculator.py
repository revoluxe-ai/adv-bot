from __future__ import annotations

from datetime import datetime, timezone


class VersionCalculator:
    @staticmethod
    def calc_version(src_ts: datetime) -> int:
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)
        return int(src_ts.timestamp() * 1000)
