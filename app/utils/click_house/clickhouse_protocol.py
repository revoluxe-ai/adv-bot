from typing import Protocol, Any, Mapping, Coroutine

from clickhouse_connect.driver.query import QueryResult


class ClickHouseClientProtocol(Protocol):
    async def query(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> QueryResult: ...

    async def insert(
        self,
        table: str,
        data: list[dict[str, Any]] | list[list[Any]],
        column_names: list[str] | None = None,
        database: str | None = None,
    ) -> Any: ...
