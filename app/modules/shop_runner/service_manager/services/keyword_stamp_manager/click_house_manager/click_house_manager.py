import logging
import time
from datetime import datetime
from typing import Sequence, Any, cast

from pathlib import Path

from clickhouse_connect.driver.query import QueryResult

from app.core.mp.wb.dto import KeywordPosition
from app.modules.common_slaves.wildberries.models import AdvSetting
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.click_house_manager.dto.keywords_jam_stat import \
    KeywordJamStat
from app.modules.shop_runner.service_manager.services.keyword_stamp_manager.keyword_stamp import (
    KeywordStamp,
)
from app.utils.ch_semaphore import anti_ch_crash_semaphore
from app.utils.click_house.client import get_clickhouse_client


logger = logging.getLogger(__name__)


# TODO: Сделать, чтобы если нет ключей, то максимальную ставку делал минимальной


class ClickHouseKeywordJamStatManager:
    @staticmethod
    async def update_stamps(stamps: list[KeywordStamp]) -> None:
        if not stamps:
            return None
        #
        # sql_path = Path(__file__).parent / "create_keyword_stamp.sql"
        # query = sql_path.read_text()

        version = int(time.time() * 1000)

        # Подготовка массива параметров
        rows: list[list[Any]] = []
        for s in stamps:
            rows.append(
                [
                    s.shop_id,
                    s.adv_id,
                    s.nmid,
                    s.text,
                    s.avr_position,
                    s.orders,
                    s.total_views,
                    s.current_cpm,
                    s.date,
                    s.timestamp,
                    version,
                ]
            )
        try:
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
        except Exception:
            logger.error("update stamps error", exc_info=True)
            raise

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
            try:
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
            except Exception:
                logger.error("update positions error", exc_info=True)
                raise

        return None

    @staticmethod
    async def get_last_positions(adv_setting: AdvSetting) -> list[KeywordJamStat]:
        sql_path = Path(__file__).parent / "sql/get_keywords_stat.sql"
        query = sql_path.read_text()
        nmid = adv_setting.nmids[0]
        adv_id = adv_setting.adv_id
        adv_type = adv_setting.type
        async with anti_ch_crash_semaphore:
            async with get_clickhouse_client() as client:
                result: QueryResult = await client.query(query, parameters={"nmid": nmid,
                                                                            "days": 7})
                rows: Sequence[tuple[str, float,  int, int, datetime]] = cast(
                    Sequence[tuple[str, float, int, int, datetime]], result.result_rows
                )
                positions: list[KeywordJamStat] = []
                for row in rows:
                    text = row[0]
                    # TODO: Сюда из рантайма дошла ошибка
                    p = int(row[1] + 0.5)
                    total_views = row[2]
                    total_orders = row[3]
                    timestamp = row[4]
                    position = KeywordJamStat(
                        nmid=nmid,
                        keyword_text=text,
                        position=p,
                        timestamp=timestamp,
                        adv_id=adv_id,
                        adv_type=adv_type,
                        total_views=total_views,
                        total_orders=total_orders,
                    )
                    positions.append(position)
        return positions
