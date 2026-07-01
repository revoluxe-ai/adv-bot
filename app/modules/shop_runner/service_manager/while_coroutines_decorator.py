"""Декоратор бесконечного цикла для фоновых корутин shop-runner.

Shop-runner использует legacy WB API (``app.core.wb_api``) и новый mp-клиент
(``app.core.mp.wb.api``); одноимённые исключения в этих пакетах — разные классы.
"""
import asyncio
import logging
from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar

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

if TYPE_CHECKING:
    from app.modules.shop_runner.wb_shop import WBShop

logger = logging.getLogger(__name__)

# Legacy WB API и mp-клиент поднимают разные классы с одинаковыми именами.
_API_FORBIDDEN_ERRORS = (LegacyApiForbiddenError, MpApiForbiddenError)
_MAX_ATTEMPTS_ERRORS = (LegacyMaxAttemptsError, MpMaxAttemptsError)


class MainCoroutineRuntimeError(RuntimeError):
    pass


T_Result = TypeVar("T_Result")
F_Spec = ParamSpec("F_Spec")


_REQUIRED_DATA_MISS_STREAKS_ATTR = "_required_data_miss_streaks"


def _get_instance_from_args(args: tuple[Any, ...]) -> Any | None:
    """Первый аргумент обёрнутой корутины — обычно CoroutinesManager (self)."""
    return args[0] if args else None


def _get_required_data_miss_streaks_dict(instance: Any) -> dict[str, int]:
    """Словарь streak по имени корутины на экземпляре (создаёт при отсутствии)."""
    streaks = getattr(instance, _REQUIRED_DATA_MISS_STREAKS_ATTR, None)
    if not isinstance(streaks, dict):
        streaks = {}
        setattr(instance, _REQUIRED_DATA_MISS_STREAKS_ATTR, streaks)
    return streaks


def _get_required_data_miss_streak(instance: Any | None, coroutine_name: str) -> int:
    """Счётчик подряд miss для пары (экземпляр магазина, имя корутины)."""
    if instance is None:
        return 0
    streaks = _get_required_data_miss_streaks_dict(instance)
    value = streaks.get(coroutine_name, 0)
    return value if isinstance(value, int) else 0


def _set_required_data_miss_streak(
    instance: Any | None, coroutine_name: str, value: int
) -> None:
    """Обновить счётчик miss на экземпляре (не в closure декоратора)."""
    if instance is None:
        return
    streaks = _get_required_data_miss_streaks_dict(instance)
    if value == 0:
        streaks.pop(coroutine_name, None)
        if not streaks and hasattr(instance, _REQUIRED_DATA_MISS_STREAKS_ATTR):
            delattr(instance, _REQUIRED_DATA_MISS_STREAKS_ATTR)
    else:
        streaks[coroutine_name] = value


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
        max_required_data_miss_attempts: подряд miss без успешного тика, затем re-raise;
            иначе env ``SHOP_RUNNER_REQUIRED_DATA_MISS_MAX_ATTEMPTS`` (30); ``<= 0`` — без лимита.
            Прочие исключения streak не сбрасывают — только успешный ``await func(...)``.

    Счётчик miss хранится на экземпляре ``CoroutinesManager`` (``_required_data_miss_streaks``),
    а не в closure декоратора — иначе все магазины в процессе делят один лимит.
    """

    def decorator(
        func: Callable[F_Spec, Awaitable[T_Result]],
    ) -> Callable[F_Spec, Coroutine[Any, Any, T_Result]]:
        coroutine_name = func.__name__
        @wraps(func)
        async def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> T_Result:
            instance: WBShop | None = _get_instance_from_args(args)
            while True:
                try:
                    try:
                        await asyncio.wait_for(*args, **kwargs, timeout=10*60)
                    except asyncio.TimeoutError:
                        logger.error(
                            "while_coroutine_decorator: timeout for %s, shop_id=%s",
                            func.__name__,
                            instance.shop_id,
                            exc_info=True,
                        )
                        raise
                    _set_required_data_miss_streak(instance, coroutine_name, 0)
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
                        streak = _get_required_data_miss_streak(
                            instance, coroutine_name
                        ) + 1
                        _set_required_data_miss_streak(
                            instance, coroutine_name, streak
                        )
                        max_attempts = required_data_miss_max_attempts(
                            max_required_data_miss_attempts
                        )
                        retry_sec = required_data_miss_retry_sec(
                            pause_on_required_data_miss
                        )
                        adv_id = getattr(exc, "adv_id", None)
                        resource = getattr(exc, "resource", "") or "unknown"
                        if max_attempts > 0 and streak >= max_attempts:
                            logger.error(
                                "Required data miss limit reached "
                                "(shop_id=%s, coroutine=%s, adv_id=%s, resource=%s, "
                                "attempts=%s/%s): %s",
                                shop_id,
                                coroutine_name,
                                adv_id,
                                resource,
                                streak,
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
                            coroutine_name,
                            adv_id,
                            resource,
                            streak,
                            max_attempts if max_attempts > 0 else "∞",
                            exc,
                            retry_sec,
                        )
                        await asyncio.sleep(retry_sec)
                        continue
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
