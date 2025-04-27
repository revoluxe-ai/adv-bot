import logging
from typing import Any

from pydantic import ValidationError

from .auction_adv import AuctionAdv
from .auto_adv import AutoAdv
from .base_adv import Adv

logger = logging.getLogger(__name__)


def get_adv_data_class(data_from_wb: dict[str, Any]) -> Adv | None:
    data = data_from_wb
    _type = data["type"]
    if _type == 8:
        try:
            return AutoAdv(**data)
        except ValidationError as exc:
            logger.error(f"{exc}", exc_info=True)
            raise
    elif _type == 9:
        try:
            return AuctionAdv(**data)
        except ValidationError as exc:
            logger.error(f"{exc}", exc_info=True)
            raise
    else:
        logger.info(f"Неизвестный типа кампании: тип {_type}")
        return None
