"""
Command для обновления ставок в поисковых кампаниях.

Этот модуль содержит команды для управления процессом обновления ставок.
"""

from dataclasses import dataclass


@dataclass
class BidUpdateForNmidCommand:
    """Команда для обновления одной ставки."""
    adv_id: int
    nmid: int
    new_bid: int

    def __post_init__(self):
        """Валидация после инициализации."""
        if self.new_bid < 0:
            raise ValueError(f"new_bid must be positive, got {self.new_bid}")
        if self.adv_id <= 0:
            raise ValueError(f"adv_id must be positive, got {self.adv_id}")
        if self.nmid <= 0:
            raise ValueError(f"nmid must be positive, got {self.nmid}")

#
# @dataclass
# class UpdateBidsBatchCommandForAdv_id:
#     """Команда для батчевого обновления ставок."""
#
#     shop_id: str
#     adv
#     updates: list[UpdateBidCommand]
#
#     def __post_init__(self):
#         """Валидация после инициализации."""
#         if not self.updates:
#             raise ValueError("updates list cannot be empty")
#         if len(self.updates) > 50:
#             raise ValueError(f"Batch size cannot exceed 50, got {len(self.updates)}")
#
#     def split_by_adv(self) -> dict[int, list[UpdateBidCommand]]:
#         """Группирует обновления по adv_id."""
#         grouped = {}
#         for update in self.updates:
#             if update.adv_id not in grouped:
#                 grouped[update.adv_id] = []
#             grouped[update.adv_id].append(update)
#         return grouped
#
#
# @dataclass
# class UpdateBidResult:
#     """Результат обновления ставки."""
#
#     adv_id: int
#     nmid: int
#     success: bool
#     old_bid: Optional[int] = None
#     new_bid: Optional[int] = None
#     error: Optional[str] = None
#
#     @property
#     def is_changed(self) -> bool:
#         """Проверяет, изменилась ли ставка."""
#         return self.success and self.old_bid != self.new_bid
