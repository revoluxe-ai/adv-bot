from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo


class BucketCalculator:
    def __init__(self, tz_name: str = "Europe/Moscow") -> None:
        self._tz = ZoneInfo(tz_name)

    def calc_bucket_start(self, src_ts: datetime) -> datetime:
        if src_ts.tzinfo is None:
            src_ts = src_ts.replace(tzinfo=timezone.utc)
        localized = src_ts.astimezone(self._tz)
        minute = (localized.minute // 15) * 15
        bucket_start = localized.replace(
            minute=minute, second=0, microsecond=0
        )
        return bucket_start
