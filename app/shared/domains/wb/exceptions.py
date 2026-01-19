class NotEnoughBalanceOnShopError(Exception):
    """Raised when a shop does not have enough balance for operations."""

    adv_id: int | None = None
