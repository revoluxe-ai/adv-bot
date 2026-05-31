"""Бесконечный цикл shop-корутин с паузами; отдельный backoff при PoolTimeout saturation."""

import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, ParamSpec, TypeVar

import httpcore
import httpx
from sqlalchemy.exc import InterfaceError

from app.core.mp.wb.api.excs import MaxAttemptsError as MpMaxAttemptsError
from app.core.mp.wb.api.excs import PoolTimeoutError
from app.core.wb_api.exceptions import ApiForbiddenError
from app.core.wb_api.exceptions import MaxAttemptsError as LegacyMaxAttemptsError
from app.modules.shop_runner.service_manager.exc import StopShopUpdateException
from app.modules.shop_runner.service_manager.exceptions import NotFoundActiveAdvCompany

logger = logging.getLogger(__name__)

# После tick timeout даём finally внутри func завершить async cleanup (shield).
TICK_FINALLY_GRACE_SECONDS = 30

# Длинная пауза между tick при исчерпании pool/retry (снижает offered-load storm).
PROMOTION_POOL_ERROR_BACKOFF_SEC = 90


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


def _get_tick_context_for_log(
    args: tuple[Any, ...], kwargs: dict[str, Any]
) -> dict[str, str]:
    """Контекст для логов tick: shop_id, cabinet_id, adv_id (если доступны)."""
    context: dict[str, str] = {"shop_id": _get_shop_id_for_log(args)}
    if not args:
        return context
    obj = args[0]
    wb_api = getattr(obj, "_wb_api", None)
    wb_cabinet = getattr(wb_api, "wb_cabinet", None) if wb_api is not None else None
    if wb_cabinet is not None:
        cabinet_id = getattr(wb_cabinet, "id", None)
        if cabinet_id not in (None, ""):
            context["cabinet_id"] = str(cabinet_id)
    for key in ("adv_id", "cabinet_id", "shop_id"):
        value = kwargs.get(key)
        if value not in (None, ""):
            context[key] = str(value)
    return context


def is_pool_timeout_related(exc: BaseException) -> bool:
    """True, если ошибка связана с исчерпанием HTTP pool (PoolTimeout / MaxAttempts после pool)."""
    if isinstance(exc, PoolTimeoutError):
        return True
    if isinstance(exc, (httpcore.PoolTimeout, httpx.PoolTimeout)):
        return True
    if isinstance(exc, (MpMaxAttemptsError, LegacyMaxAttemptsError)):
        if str(exc).startswith("PoolTimeout:"):
            return True
    seen: set[int] = set()
    cause: BaseException | None = exc.__cause__
    while cause is not None and id(cause) not in seen:
        seen.add(id(cause))
        if is_pool_timeout_related(cause):
            return True
        cause = cause.__cause__
    return False


def resolve_error_pause_seconds(exc: BaseException, pause_on_error: int) -> int:
    """Пауза после ошибки tick: длинная при pool saturation, иначе ``pause_on_error``."""
    if is_pool_timeout_related(exc):
        return PROMOTION_POOL_ERROR_BACKOFF_SEC
    return pause_on_error


def while_coroutine_decorator(
    pause_on_success: int,
    pause_on_error: int = 5,
    *,
    timeout_sec: int | None = None,
) -> Callable[
    [Callable[F_Spec, Awaitable[T_Result]]],
    Callable[F_Spec, Coroutine[Any, Any, T_Result]],
]:
    """Бесконечный цикл вызова ``func`` с паузами.

    ``timeout_sec``: если задан, один проход ``func`` ограничивается ``asyncio.wait_for``.
    На ``TimeoutError`` tick прерывается, пишется ERROR и цикл продолжается после ``pause_on_error``.
    """

    def decorator(
        func: Callable[F_Spec, Awaitable[T_Result]],
    ) -> Callable[F_Spec, Coroutine[Any, Any, T_Result]]:
        @wraps(func)
        async def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> T_Result:
            loop = asyncio.get_running_loop()
            while True:
                tick_started_at = loop.time()
                try:
                    if timeout_sec is None:
                        await func(*args, **kwargs)
                    else:
                        tick_task = asyncio.create_task(func(*args, **kwargs))
                        try:
                            await asyncio.wait_for(tick_task, timeout=timeout_sec)
                        except asyncio.TimeoutError:
                            try:
                                await asyncio.wait_for(
                                    asyncio.shield(tick_task),
                                    timeout=TICK_FINALLY_GRACE_SECONDS,
                                )
                            except (
                                asyncio.TimeoutError,
                                asyncio.CancelledError,
                            ):
                                pass
                            raise
                    await asyncio.sleep(pause_on_success)
                    continue
                except asyncio.TimeoutError:
                    elapsed = loop.time() - tick_started_at
                    ctx = _get_tick_context_for_log(args, kwargs)
                    logger.error(
                        "Таймаут tick корутины "
                        "(coroutine=%s, timeout_sec=%s, elapsed=%.3f, shop_id=%s, "
                        "cabinet_id=%s, adv_id=%s)",
                        func.__name__,
                        timeout_sec,
                        elapsed,
                        ctx.get("shop_id", "—"),
                        ctx.get("cabinet_id", "—"),
                        ctx.get("adv_id", "—"),
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_on_error)
                except InterfaceError as exc:
                    logger.exception(f"Корутина: {func.__name__}")
                    await asyncio.sleep(
                        resolve_error_pause_seconds(exc, pause_on_error)
                    )
                except ApiForbiddenError:
                    raise
                except NotFoundActiveAdvCompany as exc:
                    logger.info("Нет активных кампаний: %s", exc)
                    raise StopShopUpdateException from exc
                except StopShopUpdateException as exc:
                    logger.info("Коробка остановлена: %s", exc)
                    break
                except (MpMaxAttemptsError, LegacyMaxAttemptsError) as exc:
                    pause_sec = resolve_error_pause_seconds(exc, pause_on_error)
                    logger.error(
                        "Максимальное количество попыток для %s достигнуто: %s "
                        "(error_pause_sec=%s pool_timeout=%s)",
                        func.__name__,
                        exc,
                        pause_sec,
                        is_pool_timeout_related(exc),
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_sec)
                except PoolTimeoutError as exc:
                    pause_sec = resolve_error_pause_seconds(exc, pause_on_error)
                    logger.warning(
                        "PoolTimeout в корутине %s, пауза %ss перед следующим tick "
                        "(shop_id=%s)",
                        func.__name__,
                        pause_sec,
                        _get_shop_id_for_log(args),
                    )
                    await asyncio.sleep(pause_sec)
                except Exception as exc:
                    shop_id = _get_shop_id_for_log(args)
                    pause_sec = resolve_error_pause_seconds(exc, pause_on_error)
                    logger.error(
                        "Ошибка (shop_id=%s, coroutine=%s, error_pause_sec=%s): %s",
                        shop_id,
                        func.__name__,
                        pause_sec,
                        exc,
                        exc_info=True,
                    )
                    await asyncio.sleep(pause_sec)

        return wrapper

    return decorator
