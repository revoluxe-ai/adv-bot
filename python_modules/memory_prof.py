import functools
import logging
import tracemalloc
from typing import TypeVar, ParamSpec, Callable

logger = logging.getLogger(__name__)

T_Result = TypeVar("T_Result")
F_Spec = ParamSpec("F_Spec")


PROJECT_ROOT = "app"


def profile_memory_decorator(func: Callable[F_Spec, T_Result]) -> Callable[
    F_Spec,
    T_Result,
]:
    @functools.wraps(func)
    def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> T_Result:
        tracemalloc.start()
        snapshot_before = tracemalloc.take_snapshot()
        result: T_Result = func(*args, **kwargs)
        snapshot_after = tracemalloc.take_snapshot()
        stats = snapshot_after.compare_to(snapshot_before, "lineno")

        # Фильтруем только строки из твоего проекта
        # filtered_stats = [
        #     stat
        #     for stat in stats
        #     if stat.size_diff > 0
        #     and stat.traceback[0].filename.startswith(PROJECT_ROOT)
        # ]
        #
        total_increase = sum(stat.size_diff for stat in stats)
        if total_increase > 0:
            logging.warning(
                f"Функция {func.__name__} увеличила память на {total_increase / 1024:.2f} КБ"
            )
            # По желанию выводим топ-5 строк с приростом
            for stat in stats[:5]:
                frame = stat.traceback[0]
                logging.warning(
                    f"  +{stat.size_diff / 1024:.2f} КБ {frame.filename}:{frame.lineno}"
                )
        tracemalloc.stop()
        return result

    return wrapper
