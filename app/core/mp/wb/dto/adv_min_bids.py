from dataclasses import dataclass


@dataclass
class AdvMinNmidsBids:
    """DTO для минимальных ставок по nmids в РК Wildberries.

    Attributes:
        auto: Словарь {nmid: min_cpm} для автоматического размещения (COMBINED)
        search: Словарь {nmid: min_cpm} для поискового размещения
    """
    auto: dict[int, int]
    search: dict[int, int]
