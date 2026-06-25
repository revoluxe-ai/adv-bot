"""Расчёт следующей ставки для кластера.

Правило минимума площадки vs потолка пользователя (``max_bid`` / max_cpm в инпуте):

- **Режим snap** (``snap_to_min_bid_no_keyword_target``): целевая ставка — минимум WB
  (``min_bid``). Потолок пользователя **не** ограничивает эту ветку: если минимум площадки
  выше max_cpm, всё равно возвращаем ``min_bid`` со статусом GOOD — иначе нельзя
  корректно выставить ставку на WB. Результат **не зависит** от ``target_position``
  (в т.ч. ``None``) и от ``predict_target_bids``.

- **Обычный режим**: сначала считаем кандидата (predict / шаг), применяем потолок
  ``new_bid >= max_bid → max_bid``, затем классическую развилку с ``min_bid``.
  Если после клампа по max итог оказался **ниже** платформенного ``min_bid`` (в т.ч. когда
  ``min_bid > max_bid``), поднимаем до ``min_bid`` и ставим BAD — та же идея, что в snap,
  но здесь это конфликт настроек/рынка, а не осознанный «только минимум» режим.
"""

from app.shared.domains.wb.dto.redis_keyword_bidder_status_manager.bidder_keyword_status import BidderKeywordStatus
from .calculation_input import CalculationInput
from .update_bids_command import DirectEnum, NewBid
import logging

logger = logging.getLogger(__name__)


def _resolve_direct(current_position: float, target_position: int) -> DirectEnum:
    if current_position > target_position:
        return DirectEnum.UP
    return DirectEnum.DOWN


def _resolve_effective_step(calculation_input: CalculationInput, direct: DirectEnum) -> int:
    base_step = max(1, calculation_input.step)
    prev_step = calculation_input.prev_step
    prev_direct = calculation_input.prev_direct
    if prev_step is None or prev_step <= 0 or prev_direct is None:
        return base_step
    if prev_direct == direct:
        return min(prev_step * 2, base_step)
    return max(prev_step // 2, 1)


def _resolve_predict_bid(
    calculation_input: CalculationInput, target_position: int
) -> int | None:
    predict_map = calculation_input.predict_target_bids
    if not predict_map:
        return None
    cluster_map = predict_map.get(calculation_input.cluster)
    if not cluster_map:
        return None
    predict_bid = cluster_map.get(target_position)
    if predict_bid is None:
        return None
    return int(round(predict_bid))


def new_bid_calculate(calculation_input: CalculationInput) -> NewBid | None:
    """Вернуть новую ставку или ``None``, если менять нечего / нет ``min_bid``.

    См. модульный докстринг: ветка ``snap_to_min_bid_no_keyword_target`` не режет по
    ``max_bid`` и не использует ``target_position``; в обычной ветке нужен
    ``target_position`` (иначе ``None`` в ответе и запись в лог). После ограничения
    сверху гарантируется ``new_bid >= min_bid`` при известном ``min_bid``.
    """
    current_bid = calculation_input.current_bid
    min_bid: int | None = calculation_input.min_bid
    if calculation_input.snap_to_min_bid_no_keyword_target:
        if min_bid is None:
            logger.error("Нет минимальной ставки: не могу снизить ставку!!!")
            return None
        new_bid = min_bid
        if new_bid == current_bid:
            return None
        direct = DirectEnum.DOWN if new_bid < current_bid else DirectEnum.UP
        effective_step = max(1, calculation_input.step)
        return NewBid(
            search_adv_id=calculation_input.search_adv_id,
            nmid=calculation_input.nmid,
            new_bid=new_bid,
            bidder_keyword_status=BidderKeywordStatus.GOOD,
            cluster=calculation_input.cluster,
            step=effective_step,
            direct=direct,
        )

    target_position = calculation_input.target_position
    if target_position is None:
        logger.error(
            "Нет target_position при snap_to_min_bid_no_keyword_target=False: "
            "adv_id=%s nmid=%s cluster=%s",
            calculation_input.search_adv_id,
            calculation_input.nmid,
            calculation_input.cluster,
        )
        return None

    current_position = calculation_input.current_position
    if current_position < 1: # фоллбек на всякий случай
        current_position  = 1
    direct = _resolve_direct(current_position, target_position)
    effective_step = _resolve_effective_step(calculation_input, direct)
    predict_bid_for_target_position = _resolve_predict_bid(
        calculation_input, target_position
    )
    max_bid = calculation_input.max_bid
    new_bid: int

    if (
        direct == DirectEnum.UP
        and predict_bid_for_target_position is not None
        and predict_bid_for_target_position > current_bid
    ):
        new_bid = predict_bid_for_target_position
    elif (
        direct == DirectEnum.DOWN
        and predict_bid_for_target_position is not None
        and predict_bid_for_target_position < current_bid
    ):
        new_bid = predict_bid_for_target_position
    elif direct == DirectEnum.UP:
        new_bid = current_bid + effective_step
    else:
        new_bid = current_bid - effective_step

    if new_bid >= max_bid:
        new_bid = max_bid
        bidder_keyword_status = BidderKeywordStatus.GOOD
    elif min_bid is not None and min_bid <= new_bid < max_bid:
        bidder_keyword_status = BidderKeywordStatus.GOOD
    elif min_bid is None:
        logger.error("Нет минимальной ставки: не могу снизить ставку!!!")
        return None
    else:
        new_bid = min_bid
        bidder_keyword_status = BidderKeywordStatus.BAD

    # См. модульный докстринг: max-кламп не должен оставлять ставку ниже минимума WB.
    if min_bid is not None and new_bid < min_bid:
        new_bid = min_bid
        bidder_keyword_status = BidderKeywordStatus.BAD

    if new_bid == current_bid:
        return None
    return  NewBid(
        search_adv_id=calculation_input.search_adv_id,
        nmid=calculation_input.nmid,
        new_bid=new_bid,
        bidder_keyword_status=bidder_keyword_status,
        cluster=calculation_input.cluster,
        step=effective_step,
        direct=direct,
    )





