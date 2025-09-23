from collections.abc import Awaitable
from dataclasses import dataclass


@dataclass
class UpdateBidForNmidTask:
    adv_id: int
    nmid: int
    new_bid_coro: Awaitable[int]


@dataclass
class UpdateBidsSearchAdvInShopBatch:
    shop_id: str
    __tasks: list[UpdateBidForNmidTask] | None = None

    def add_task(self, task: UpdateBidForNmidTask) -> None:
        if self.__tasks is None:
            self.__tasks = []
        self.__tasks.append(task)

    @property
    def tasks(self) -> list[UpdateBidForNmidTask]:
        if self.__tasks is None:
            return []
        return self.__tasks


# Resolved DTOs (без корутин): когда значения ставок уже вычислены


@dataclass
class UpdateBidResolvedTask:
    adv_id: int
    nmid: int
    new_bid: int


@dataclass
class UpdateBidsResolvedBatch:
    shop_id: str
    __tasks: list[UpdateBidResolvedTask] | None = None

    def add_task(self, task: UpdateBidResolvedTask) -> None:
        if self.__tasks is None:
            self.__tasks = []
        self.__tasks.append(task)

    @property
    def tasks(self) -> list[UpdateBidResolvedTask]:
        if self.__tasks is None:
            return []
        return self.__tasks
