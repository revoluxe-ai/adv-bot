from typing import Protocol, Any


class PromotionAdapterProtocol(Protocol):
    async def update_bids(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        ...