from typing import Awaitable, TypeVar
import logging
from app.core.mp.wb.api.excs import BadRequestError

logger = logging.getLogger(__name__)


T = TypeVar("T")


async def catch_special_errors(awaitable: Awaitable[T]) -> T | None:
    try:
        return await awaitable
    except BadRequestError as exc:
        raw_detail = getattr(exc, "detail", None)
        detail = raw_detail if isinstance(raw_detail, str) else str(raw_detail or "")
        if "norm_query disabled for nm" in detail.lower():
            logger.warning(detail)
            return None
        raise




