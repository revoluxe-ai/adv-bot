import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from sqlalchemy.exc import InterfaceError

from app.core.mp.wb.api.excs import MaxAttemptsError, ApiForbiddenError
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)


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
    pause_on_success: int, pause_on_error: int = 5
) -> Callable[
    [Callable[F_Spec, Awaitable[T_Result]]],
    Callable[F_Spec, Coroutine[Any, Any, T_Result]],
]:
    def decorator(
        func: Callable[F_Spec, Awaitable[T_Result]],
    ) -> Callable[F_Spec, Coroutine[Any, Any, T_Result]]:
        @wraps(func)
        async def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> T_Result:
            while True:
                try:
                    await func(*args, **kwargs)
                    await asyncio.sleep(pause_on_success)
                    continue
                except InterfaceError:
                    logger.exception(f"Корутина: {func.__name__}")
                    await asyncio.sleep(pause_on_error)
                except ApiForbiddenError:
                    raise
                except NotFoundActiveAdvCompany as exc:
                    logger.info("Нет активных кампаний: %s", exc)
                    raise StopShopUpdateException from exc
                except StopShopUpdateException as exc:
                    logger.info("Коробка остановлена: %s", exc)
                    break
                except MaxAttemptsError as exc:
                    logger.error(
                        f"Максимальное количество попыток для {func.__name__} достигнуто: {exc}",
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_on_error)
                except Exception as exc:
                    shop_id = _get_shop_id_for_log(args)
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
