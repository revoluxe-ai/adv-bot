from dataclasses import dataclass

from app.modules.common_slaves.wildberries.models.enums import KeywordStrategyMode


@dataclass(frozen=True)
class AdvIdItemCalculateData:
    """Данные одной ячейки торгов (поисковая РК × nmid × кластер).

    ``search_adv_id`` — Search (auction) adv_id: WB API и Redis ``cluster-bid:*``.
    ``auto_adv_id`` — Auto (original) adv_id: plan/fact CH и overspend gate V3 cap.

    ``max_cpm`` — потолок пользователя; в калькулятор уходит как ``max_bid``.

    ``snap_to_min_bid_no_keyword_target``: если True, при расчёте ставки используется
    ветка «сразу на минимум площадки» без ограничения этим потолком (см. докстринг
    ``CalculationInput`` / ``new_bid_calculate``). Выставляется оркестратором, когда
    для фразы нет своей целевой позиции при включённом per-keyword режиме; тогда
    ``target_position`` может быть ``None`` (цель по позиции не задана, калькулятор
    в snap-ветке поле не использует).
    """
    search_adv_id: int
    adv_id: int
    nmid: int
    cluster: str
    current_position: float
    target_position: int | None
    max_cpm: int
    step: int
    current_cpm: int | None
    keyword_setting_original_id: int
    strategy_mode: KeywordStrategyMode | None = None
    v3_managed: bool = False
    snap_to_min_bid_no_keyword_target: bool = False
