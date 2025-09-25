import asyncio
from abc import ABC, abstractmethod
from typing import Any, Awaitable, List, Tuple


class FutureGetterBase(ABC):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._coros: List[Tuple[asyncio.Future, Awaitable, tuple, dict]] = []

    def _get_future(self, *args, **kwargs) -> asyncio.Future:
        future = self._loop.create_future()
        coro = self._fetch(*args, **kwargs)
        self._coros.append((future, coro, args, kwargs))
        return future

    async def run(self):
        tasks = [coro for (_, coro, _, _) in self._coros]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (future, _, _, _), result in zip(self._coros, results):
            if isinstance(result, Exception):
                if not future.done():
                    future.set_exception(result)
            else:
                if not future.done():
                    future.set_result(result)
        self._coros.clear()

    @abstractmethod
    async def _fetch(self, *args, **kwargs) -> Any:
        pass

    @abstractmethod
    def get_future(self, *args, **kwargs) -> asyncio.Future:
        pass
