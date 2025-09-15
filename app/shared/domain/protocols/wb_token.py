import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class WBTokenProtocol(Protocol):
    api_key: str
    user_id: int
    active: bool
    shop_id: str | None

    def __repr__(self) -> str: ...

    def check_valid(self) -> bool: ...
    def get_payload(self, key: str) -> str | int | None: ...
    def get_shop_id_from_token(self) -> str: ...

    @property
    def expires(self) -> datetime.datetime: ...

    @property
    def read_only(self) -> bool: ...

    @property
    def categories(self) -> set[str]: ...

    @property
    def hash(self) -> str: ...

    @property
    def is_expired(self) -> bool: ...
