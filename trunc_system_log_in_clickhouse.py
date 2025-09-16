import dotenv

dotenv.load_dotenv()
import asyncio
import logging

from app.utils.click_house.client import get_clickhouse_client

logger = logging.getLogger(__name__)

async def truncate_logs():
    tables = [
        "system.processors_profile_log",
        "system.metric_log",
        "system.query_log",
        "system.text_log",
        "system.asynchronous_metric_log",
        "system.query_metric_log",
        "system.part_log",
        "system.trace_log",
        "system.error_log"
    ]

    async with get_clickhouse_client() as client:
        for table in tables:
            print(f"Truncating {table}...")
            await client.query(f"TRUNCATE TABLE {table}")

        print("Truncate completed!")


async def main():
    while True:
        try:
            await truncate_logs()
        except Exception:
            logger.error('Ошибка', exc_info=True)
        await asyncio.sleep(60 * 10)

if __name__ == "__main__":
    asyncio.run(main())
