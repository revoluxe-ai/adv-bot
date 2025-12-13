from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Mapped


@runtime_checkable
class AdvProtocol(Protocol):
    @property
    def adv_id(self) -> int | Mapped[int]: ...