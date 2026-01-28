import asyncio
import csv
from pathlib import Path
from typing import AsyncIterator

from app.modules.common_slaves.wildberries.models import WBCabinet
from scripts.get_users.get_users import get_users
from scripts.get_users.filters.filters import get_non_zero_users

from app.modules.balance_manager.balance_service import get_cabinet_balance
from scripts.users_communicate_module.main_user_generator import get_users_iterator

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
    ]
    written = 0

    users_async_iterator = await get_users_iterator(batch_size=batch_size)
    with output.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        async for user in users_async_iterator:
            for user_cabinet in user.wb_user_cabinets:
                cabinet: WBCabinet = user_cabinet.wb_cabinet
                balance_plus_bonus = cabinet.calculated_balance + cabinet.calculated_bonus
                active_campaigns = sum(
                    1
                    for adv in getattr(cabinet, "adv_settings", []) or []
                    if adv.bot_active
                )

                writer.writerow(
                    {
                        "user_id": user.id,
                        "telegram_id": user.user_telegram_id,
                        "login": user.username or "",
                        "cabinet_name": user_cabinet.name,
                        "shop_id": cabinet.shop_id,
                        "balance": cabinet.calculated_balance,
                        "bonus": cabinet.calculated_bonus,
                        "balance_plus_bonus": balance_plus_bonus,
                        "active_campaigns": active_campaigns,
                        "has_active_campaign": active_campaigns > 0,
                    }
                )
                written += 1
                if limit is not None and written >= limit:
                    return output

    return output


if __name__ == '__main__':
    asyncio.run(export_users_to_csv(batch_size=BATCH_SIZE))
