from typing import Awaitable, TypeVar
import logging
from app.core.mp.wb.api.excs import BadRequestError

logger = logging.getLogger(__name__)


T = TypeVar("T")


async def catch_special_errors(awaitable: Awaitable[T]) -> T | None:
    try:
        return await awaitable
    except BadRequestError as exc:
        if (detail :=exc.detail) is not None:
            if "norm_query disabled for nm" in detail:
                logger.warning(exc.detail)
                return None
        raise




