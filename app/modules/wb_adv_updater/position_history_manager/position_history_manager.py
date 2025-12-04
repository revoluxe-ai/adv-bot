from clickhouse_connect.driver.query import QueryResult

from app.core.clickhouse_manager import BaseClickHouseManager
from .dto.position_history import  PositionHistory, Position
from app.utils.click_house.client import get_clickhouse_client as get_client


class PositionHistoryManager(BaseClickHouseManager):

    async def get_position_history(self, nmid: int, last_days: int) -> PositionHistory:
        query = self._get_query('get_position_history')
        async with get_client() as client:
            result: QueryResult = await client.query(query, parameters={'nmid': nmid,
                                                     "last_days": last_days})
        positions: list[Position] = []
        for obj in result.named_results(): # pyright: ignore
            position = Position.model_validate(obj)
            positions.append(position)
        position_history = PositionHistory(nmid=nmid,
                                           positions=positions)
        return position_history