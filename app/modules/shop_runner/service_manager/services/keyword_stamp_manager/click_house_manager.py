import logging
import time
from typing import Any

from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.keyword_stamp import (
    KeywordStamp,
)
from app.utils.click_house.client import get_clickhouse_client


logger = logging.getLogger(__name__)


# TODO: Сделать, чтобы если нет ключей, то максимальную ставку делал минимальной


class ClickHouseKeywordStampManager:

    async def update_stamps(self, stamps: list[KeywordStamp]) -> None:
        if not stamps:
            return

        async with get_clickhouse_client() as client:
            version = str(time.time())
            # Подготовим данные для пакетной вставки
            data: list[dict[str, Any]] = []
            for stamp in stamps:
                data.append(
                    {
                        "shop_id": stamp.shop_id,
                        "adv_id": stamp.adv_id,
                        "nmid": stamp.nmid,
                        "text": stamp.text,
                        "avr_position": stamp.avr_position,
                        "orders": stamp.orders,
                        "date": stamp.date,
                        "total_views": stamp.total_views,
                        "current_cpm": stamp.current_cpm,
                        "timestamp": stamp.timestamp,
                        "version": version,
                    }
                )

            # Пакетная вставка всех строк за один запрос
            await client.insert(
                table="default_db.keyword_stamp",
                data=data,
            )
