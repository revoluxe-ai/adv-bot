"""Декоратор бесконечного цикла для фоновых корутин shop-runner.

Shop-runner использует legacy WB API (``app.core.wb_api``) и новый mp-клиент
(``app.core.mp.wb.api``); одноимённые исключения в этих пакетах — разные классы.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from sqlalchemy.exc import InterfaceError

from app.core.mp.wb.api.excs import ApiForbiddenError as MpApiForbiddenError
from app.core.mp.wb.api.excs import MaxAttemptsError as MpMaxAttemptsError
from app.core.wb_api.exceptions import ApiForbiddenError as LegacyApiForbiddenError
from app.core.wb_api.exceptions import MaxAttemptsError as LegacyMaxAttemptsError
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany
from app.modules.shop_runner.required_data_miss import (
    is_required_data_miss,
    required_data_miss_max_attempts,
    required_data_miss_retry_sec,
)

logger = logging.getLogger(__name__)

# Legacy WB API и mp-клиент поднимают разные классы с одинаковыми именами.
_API_FORBIDDEN_ERRORS = (LegacyApiForbiddenError, MpApiForbiddenError)
_MAX_ATTEMPTS_ERRORS = (LegacyMaxAttemptsError, MpMaxAttemptsError)


class MainCoroutineRuntimeError(RuntimeError):
    pass


T_Result = TypeVar("T_Result")
F_Spec = ParamSpec("F_Spec")


def _get_shop_id_for_log(args: tuple[Any, ...]) -> str:
    """Extract shop_id from first argument (expected: CoroutinesManager instance)."""
    if not args:
        return "missing_shop_id(no_self)"
    obj = args[0]
    shop_id = getattr(obj, "shop_id", None)
    if shop_id not in (None, ""):
        return str(shop_id)
    wb_api = getattr(obj, "_wb_api", None)
    if wb_api is not None:
        wb_shop_id = getattr(wb_api, "shop_id", None)
        if wb_shop_id not in (None, ""):
            return str(wb_shop_id)
    return f"missing_shop_id(type={type(obj).__name__})"


def while_coroutine_decorator(
    pause_on_success: int,
    pause_on_error: int = 5,
    *,
    pause_on_required_data_miss: int | None = None,
    max_required_data_miss_attempts: int | None = None,
) -> Callable[
    [Callable[F_Spec, Awaitable[T_Result]]],
    Callable[F_Spec, Coroutine[Any, Any, T_Result]],
]:
    """Бесконечный цикл корутины с паузами после успеха/ошибок.

    Args:
        pause_on_success: sleep (сек) после успешного тика.
        pause_on_error: sleep (сек) после обычной ошибки.
        pause_on_required_data_miss: sleep при miss обязательных данных; иначе env
            ``SHOP_RUNNER_REQUIRED_DATA_MISS_RETRY_SEC`` (по умолчанию 60).
        max_required_data_miss_attempts: подряд miss без успеха, затем re-raise;
            иначе env ``SHOP_RUNNER_REQUIRED_DATA_MISS_MAX_ATTEMPTS`` (30); ``<= 0`` — без лимита.
    """

    def decorator(
        func: Callable[F_Spec, Awaitable[T_Result]],
    ) -> Callable[F_Spec, Coroutine[Any, Any, T_Result]]:
        required_data_miss_streak = 0

        @wraps(func)
        async def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> T_Result:
            nonlocal required_data_miss_streak
            while True:
                try:
                    await func(*args, **kwargs)
                    required_data_miss_streak = 0
                    await asyncio.sleep(pause_on_success)
                    continue
                except InterfaceError:
                    logger.exception(f"Корутина: {func.__name__}")
                    await asyncio.sleep(pause_on_error)
                except _API_FORBIDDEN_ERRORS:
                    raise
                except NotFoundActiveAdvCompany as exc:
                    logger.info("Нет активных кампаний: %s", exc)
                    raise StopShopUpdateException from exc
                except StopShopUpdateException as exc:
                    logger.info("Коробка остановлена: %s", exc)
                    break
                except _MAX_ATTEMPTS_ERRORS as exc:
                    logger.error(
                        f"Максимальное количество попыток для {func.__name__} достигнуто: {exc}",
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_on_error)
                except Exception as exc:
                    shop_id = _get_shop_id_for_log(args)
                    if is_required_data_miss(exc):
                        required_data_miss_streak += 1
                        max_attempts = required_data_miss_max_attempts(
                            max_required_data_miss_attempts
                        )
                        retry_sec = required_data_miss_retry_sec(
                            pause_on_required_data_miss
                        )
                        adv_id = getattr(exc, "adv_id", None)
                        resource = getattr(exc, "resource", "") or "unknown"
                        if max_attempts > 0 and required_data_miss_streak > max_attempts:
                            logger.error(
                                "Required data miss limit reached "
                                "(shop_id=%s, coroutine=%s, adv_id=%s, resource=%s, "
                                "attempts=%s/%s): %s",
                                shop_id,
                                func.__name__,
                                adv_id,
                                resource,
                                required_data_miss_streak,
                                max_attempts,
                                exc,
                                exc_info=True,
                            )
                            raise
                        logger.warning(
                            "Required data miss (shop_id=%s, coroutine=%s, adv_id=%s, "
                            "resource=%s, attempt=%s/%s): %s; retry in %ss "
                            "(snapshot updater warmup)",
                            shop_id,
                            func.__name__,
                            adv_id,
                            resource,
                            required_data_miss_streak,
                            max_attempts if max_attempts > 0 else "∞",
                            exc,
                            retry_sec,
                        )
                        await asyncio.sleep(retry_sec)
                        continue
                    required_data_miss_streak = 0
                    logger.error(
                        "Ошибка (shop_id=%s, coroutine=%s): %s",
                        shop_id,
                        func.__name__,
                        exc,
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_on_error)

        return wrapper

    return decorator
