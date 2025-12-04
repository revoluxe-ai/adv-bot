import inspect
from abc import ABC
from pathlib import Path


class BaseClickHouseManager(ABC):

    @classmethod
    def _get_query(cls, query_file_name: str) -> str:
        file_path = Path(inspect.getfile(cls))
        sql_path = file_path.parent / "sql" / f"{query_file_name}.sql"
        return sql_path.read_text(encoding="utf-8")


