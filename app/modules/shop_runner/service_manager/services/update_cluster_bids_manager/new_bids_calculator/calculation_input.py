from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .update_bids_command import DirectEnum


@dataclass(frozen=True)
class CalculationInput:
    """Вход калькулятора ставки по кластеру (nmid + cluster).

    ``max_bid`` — потолок пользователя (max_cpm). ``min_bid`` — минимальная ставка
    площадки для nm_id (может отсутствовать в кэше → ``None``).

    При ``snap_to_min_bid_no_keyword_target`` калькулятор идёт в отдельную ветку:
    целевая ставка = ``min_bid``; ``max_bid`` на эту ветку **не** накладывается
    (минимум WB важнее потолка пользователя). Поле ``target_position`` в этой ветке
    **не используется** (допустимо ``None``, если нет пер-фразовой цели по позиции).
    В обычной ветке ``target_position`` должно быть задано (``int``). Потолок применяется,
    но итог не остаётся ниже ``min_bid``, если оно известно (см. ``new_bid_calculate``).
    """

    search_adv_id: int
    nmid: int
    cluster: str
    current_bid: int
    current_position: float
    target_position: int | None
    step: int
    max_bid: int
    min_bid: int | None
    predict_target_bids: dict[str, dict[int, int]] | None
    prev_direct: "DirectEnum | None" = None
    prev_step: int | None = None
    snap_to_min_bid_no_keyword_target: bool = False
