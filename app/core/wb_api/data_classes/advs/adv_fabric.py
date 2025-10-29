import logging
from typing import Any, assert_never, cast

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
            return cast(Adv, AutoAdv(data))
        except ValidationError as exc:
            logger.error(f"{exc}")
            raise exc
    elif _type == 9:
        try:
            return cast(Adv, AuctionAdv(data))
        except ValidationError as exc:
            logger.error(f"Validation error creating AuctionAdv: {exc}")
            raise exc
    else:
        logger.error(f"Неожиданный тип кампании: {_type}, ожидался 9 (аукцион)")
        # Use assert_never for type safety and exhaustiveness checking
        # assert_never(_type) # Закомментировано, так как _type может быть не Literal, и assert_never будет генерировать ошибку
        return None # Добавлено, чтобы функция всегда возвращала значение
