import asyncio
import csv
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from scripts.users_communicate_module.main_user_generator import get_users_iterator

DEFAULT_CSV_PATH = Path("scripts/users_csv_exporter/all_users.csv")
DEFAULT_XLSX_PATH = Path("scripts/users_csv_exporter/all_users.xlsx")

BATCH_SIZE = 30

_FIELDNAMES = [
    "user_id",
    "telegram_id",
    "login",
    "cabinet_name",
    "shop_id",
    "balance",
    "bonus",
    "balance_plus_bonus",
    "last_30_days_topups",
    "last_30_days_orders_sum_rub",
    "last_30_days_buyouts_sum_rub",
    "active_campaigns",
    "has_active_campaign",
    "tariff_mode",
    "tariff_count",
    "tariff_price_per_adv",
    "tariff_total_per_month",
    "tariff_total_per_day",
    "balance_days_left",
]


async def export_users_to_csv(
    dest_path: Path | str = DEFAULT_CSV_PATH,
    *,
    limit: int | None = None,
    batch_size: int,
) -> Path:
    """Write per-cabinet rows into ``dest_path`` (CSV, UTF-8)."""
    output = Path(dest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    users_async_iterator = await get_users_iterator()
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=_FIELDNAMES)
        writer.writeheader()
        async for user in users_async_iterator:
            user_base = {
                "user_id": user.user_id,
                "telegram_id": user.telegram_id,
                "login": user.login,
            }
            for user_cabinet in user.cabinets:
                writer.writerow({**user_base, **asdict(user_cabinet)})
                written += 1
                if limit is not None and written >= limit:
                    return output
    return output


async def export_users_to_excel(
    dest_path: Path | str = DEFAULT_XLSX_PATH,
    *,
    limit: int | None = None,
    batch_size: int,
) -> Path:
    """Write per-cabinet rows into ``dest_path`` (.xlsx)."""
    output = Path(dest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, object]] = []
    written = 0
    users_async_iterator = await get_users_iterator()
    async for user in users_async_iterator:
        user_base = {
            "user_id": user.user_id,
            "telegram_id": user.telegram_id,
            "login": user.login,
        }
        for user_cabinet in user.cabinets:
            rows.append({**user_base, **asdict(user_cabinet)})
            written += 1
            if limit is not None and written >= limit:
                break
        if limit is not None and written >= limit:
            break
    frame = pd.DataFrame(rows, columns=_FIELDNAMES)
    frame.to_excel(output, index=False)
    return output


if __name__ == "__main__":
    _ = asyncio.run(export_users_to_excel(batch_size=BATCH_SIZE))
