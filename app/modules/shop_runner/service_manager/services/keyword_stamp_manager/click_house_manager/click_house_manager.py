import logging
import time
from typing import Sequence, Any

# from pathlib import Path

from app.core.mp.wb.dto import KeywordPosition
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.keyword_stamp import (
    KeywordStamp,
)
from app.utils.click_house.client import get_clickhouse_client


logger = logging.getLogger(__name__)


# TODO: Сделать, чтобы если нет ключей, то максимальную ставку делал минимальной


class ClickHouseKeywordStampManager:
    @staticmethod
    async def update_stamps(stamps: list[KeywordStamp]) -> None:
        if not stamps:
            return None
        #
        # sql_path = Path(__file__).parent / "create_keyword_stamp.sql"
        # query = sql_path.read_text()

        version = int(time.time() * 1000)

        # Подготовка массива параметров
        rows: list[dict[str, Any]] = []
        for s in stamps:
            rows.append(
                {
                    "shop_id": s.shop_id,
                    "adv_id": s.adv_id,
                    "nmid": s.nmid,
                    "text": s.text,
                    "avr_position": s.avr_position,
                    "orders": s.orders,
                    "total_views": s.total_views,
                    "current_cpm": s.current_cpm,
                    "date": s.date,
                    "timestamp": s.timestamp,
                    "version": version,
                }
            )

        async with get_clickhouse_client() as client:
            await client.insert(
                table="default_db.keyword_stamp",
                data=rows,
                column_names=[
                    "shop_id",
                    "adv_id",
                    "nmid",
                    "text",
                    "avr_position",
                    "orders",
                    "total_views",
                    "current_cpm",
                    "date",
                    "timestamp",
                    "version",
                ],
            )

        return None

    @staticmethod
    async def update_positions(positions: Sequence[KeywordPosition]) -> None:
        if not positions:
            return None
        # sql_path = Path(__file__).parent / "create_keyword_position.sql"
        # query = sql_path.read_text()
        rows: list[list[Any]] = []
        version = int(time.time() * 1000)
        for position in positions:
            rows.append(
                [
                    position.nmid,
                    position.text,
                    position.average_position,
                    position.total_views_avr_for_day,
                    position.orders,
                    position.date,
                    version,
                ]
            )

        async with get_clickhouse_client() as client:
            await client.insert(
                table="default_db.keyword_position_from_api",
                data=rows,
                column_names=[
                    "nmid",
                    "text",
                    "avr_position",
                    "total_views",
                    "orders",
                    "date",
                    "version",
                ],
            )


        return None
