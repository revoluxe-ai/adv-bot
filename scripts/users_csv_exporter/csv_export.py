import asyncio
import csv
from dataclasses import asdict
from pathlib import Path

from app.modules.billing.pricer.pricer import Pricer
from scripts.users_communicate_module.main_user_generator import get_users_iterator
from scripts.users_csv_exporter.dto import UserCabinetExportDTO

DEFAULT_EXPORT_PATH = Path("scripts/users_csv_exporter/with_near-payment-users.csv")


BATCH_SIZE = 30




async def export_users_to_csv(
    dest_path: Path | str = DEFAULT_EXPORT_PATH, *,
    limit: int | None = None,
    batch_size,
) -> Path:
    """Write per-cabinet rows filtered by `get_non_zero_users` into `dest_path`."""
    output = Path(dest_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "user_id",
        "telegram_id",
        "login",
        "cabinet_name",
        "shop_id",
        "balance",
        "bonus",
        "balance_plus_bonus",
        "active_campaigns",
        "has_active_campaign",
        "tariff_mode",
        "tariff_count",
        "tariff_price_per_adv",
        "tariff_total_per_month",
        "tariff_total_per_day",
        "balance_days_left",
    ]
    written = 0

    pricer = Pricer()
    users_async_iterator = await get_users_iterator(batch_size=batch_size)
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        async for user in users_async_iterator:
            for user_cabinet in user.wb_user_cabinets:
                dto = await UserCabinetExportDTO.from_models(
                    user=user, wb_user_cabinet=user_cabinet, pricer=pricer
                )
                writer.writerow(asdict(dto))
                written += 1
                if limit is not None and written >= limit:
                    return output

    return output


if __name__ == '__main__':
    asyncio.run(export_users_to_csv(batch_size=BATCH_SIZE))
