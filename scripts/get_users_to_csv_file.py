import asyncio
import csv
from pathlib import Path

from scripts.send_message.utils.get_user_with_token_without_balance import \
    iter_users_with_zero_or_negative_balance_without_active_advs


async def dump_users_to_csv(
    csv_path: str | Path,
    batch_size: int = 100,
) -> None:
    csv_path = Path(csv_path)

    # важно: newline="", иначе будут пустые строки на Windows
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["user_telegram_id", "username"])

        async for user in iter_users_with_zero_or_negative_balance_without_active_advs(
            batch_size=batch_size
        ):
            writer.writerow([
                user.user_telegram_id,
                user.username or "",
            ])

if __name__ == '__main__':
    asyncio.run(dump_users_to_csv('tg_users.csv'))
