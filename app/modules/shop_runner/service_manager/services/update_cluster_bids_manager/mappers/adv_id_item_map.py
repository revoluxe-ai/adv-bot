from dataclasses import dataclass


@dataclass(frozen=True)
class AdvIdItemCalculateData:
    """Данные одной ячейки торгов (поисковая РК × nmid × кластер).

    ``max_cpm`` — потолок пользователя; в калькулятор уходит как ``max_bid``.

    ``snap_to_min_bid_no_keyword_target``: если True, при расчёте ставки используется
    ветка «сразу на минимум площадки» без ограничения этим потолком (см. докстринг
    ``CalculationInput`` / ``new_bid_calculate``). Выставляется оркестратором, когда
    для фразы нет своей целевой позиции при включённом per-keyword режиме; тогда
    ``target_position`` может быть ``None`` (цель по позиции не задана, калькулятор
    в snap-ветке поле не использует).
    """

    adv_id: int
    nmid: int
    cluster: str
    current_position: float
    target_position: int | None
    max_cpm: int
    step: int
    current_cpm: int | None
    snap_to_min_bid_no_keyword_target: bool = False