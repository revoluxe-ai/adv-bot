import logging
from functools import wraps
from typing import (
    ParamSpec,
    TypeVar,
    Callable,
    Coroutine,
    Any,
    Awaitable,
    cast,
)

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


def neo4j_session(
    func: Callable[..., Coroutine[Any, Any, T]],
) -> Callable[..., Coroutine[Any, Any, T]]:
    @wraps(func)
    async def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
        try:
            async with self.neo4j_driver.session() as session:
                cast_func = cast(Callable[..., Coroutine[Any, Any, T]], func)(
                    self, *args, **kwargs, session=session
                )
                return await cast_func
        except Exception as e:
            logger.error(f"Neo4j error in {func.__name__}: {e}")
            raise

    return cast(Callable[..., Coroutine[Any, Any, T]], wrapper)
