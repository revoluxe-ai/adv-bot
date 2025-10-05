import logging
from typing import Any, assert_never

from pydantic import ValidationError

from .auction_adv import AuctionAdv

logger = logging.getLogger(__name__)


def get_adv_data_class(data_from_wb: dict[str, Any]) -> AuctionAdv:
    """Create AuctionAdv instance from WB API data.

    Since WB API now only returns auction campaigns (type 9),
    we always return AuctionAdv instances.
    """
    data = data_from_wb
    _type = data["type"]
    if _type == 9:
        try:
            return AuctionAdv(data)
        except ValidationError as exc:
            logger.error(f"Validation error creating AuctionAdv: {exc}")
            raise exc
    else:
        logger.error(f"Неожиданный тип кампании: {_type}, ожидался 9 (аукцион)")
        # Use assert_never for type safety and exhaustiveness checking
        assert_never(_type)
