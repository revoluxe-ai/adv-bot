"""Парсинг снимка баланса магазина для строки про кэшбек (единая логика для UI)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Mapping

MSK_TZ = timezone(timedelta(hours=3))


@dataclass(frozen=True, slots=True)
class CashbackSnapshotParsed:
    total: int
    percent_part: str
    expiration_msk: datetime | None


def parse_cashback_snapshot(
    snapshot: Mapping[str, int | str | None] | None,
) -> CashbackSnapshotParsed | None:
    """Разобрать поля кэшбека из словаря снимка баланса.

    Ключи: ``cashbacks_total``, ``cashbacks_best_percent``, ``cashbacks_earliest_expiration``.
    Возвращает ``None``, если показывать кэшбек нечего.
    """
    if not snapshot:
        return None
    total = int(snapshot.get("cashbacks_total", 0) or 0)
    if total <= 0:
        return None
    raw_exp = snapshot.get("cashbacks_earliest_expiration")
    raw_percent = snapshot.get("cashbacks_best_percent")
    percent_part = ""
    if raw_percent is not None:
        percent_part = f", до {int(raw_percent)}%"
    expiration_msk: datetime | None = None
    if raw_exp:
        try:
            dt = datetime.fromisoformat(str(raw_exp).replace("Z", "+00:00"))
            expiration_msk = dt.astimezone(MSK_TZ)
        except (ValueError, TypeError):
            expiration_msk = None
    return CashbackSnapshotParsed(
        total=total,
        percent_part=percent_part,
        expiration_msk=expiration_msk,
    )
