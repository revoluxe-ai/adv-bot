from abc import ABC, abstractmethod


class BaseWorker(ABC):

    @abstractmethod
    async def run(self) -> None:...
