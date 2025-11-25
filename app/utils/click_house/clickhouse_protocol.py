from typing import Protocol, Any, Mapping, Coroutine


class ClickHouseClientProtocol(Protocol):
    async def query(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> Any: ...

    async def insert(
        self,
        table: str,
        data: list[dict[str, Any]] | list[list[Any]],
        column_names: list[str] | None = None,
        database: str | None = None,
    ) -> Any: ...
