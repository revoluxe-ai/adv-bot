from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Mapped


@runtime_checkable
class AdvProtocol(Protocol):
    """Search auction adv_id для timestamp cluster bids."""

    @property
    def search_adv_id(self) -> int | None | Mapped[int | None]: ...