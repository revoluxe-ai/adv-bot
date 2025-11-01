from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from .utils import get_candidates_to_leader, get_leader


def get_next_raise_exponent(
    exponent_now: float,
    keywords: list[CalculatedKeyword],
) -> float | None:
    """
    Вычисляет минимальное увеличение экспоненты Δexp, при котором
    появится новый лидер с более высоким CTR.

    :param exponent_now: Текущая экспонента (в диапазоне 1–20)
    :param keywords: список ключей с атрибутами ctr и views
    :return: минимальное приращение экспоненты Δexp,
             либо None, если лидер с большим CTR невозможен
    """

    keywords = get_candidates_to_leader(keywords)
    if not keywords:
        return None  # нет кандидатов
    # Текущий вес w (из диапазона [0, 1])
    w_now = (exponent_now - 1) / 19

    # Находим текущего лидера по рейтингу
    leader = get_leader(keywords)
    ctr_L, views_L = leader.predict_ctr, leader.views

    # Отбираем кандидатов с CTR > CTR_лидера
    candidates = [kw for kw in keywords if kw.predict_ctr > ctr_L]
    if not candidates:
        return None  # нет кандидатов с большим CTR

    possible_ws: list[float] = []

    for cand in candidates:
        ctr_i, views_i = cand.predict_ctr, cand.views
        numerator = ctr_L * views_L - ctr_i * views_i
        denominator = ctr_i - ctr_i * views_i - ctr_L + ctr_L * views_L

        if denominator == 0:
            continue  # прямые параллельны, не пересекутся

        w_new = numerator / denominator

        # Нас Интересует только будущие пересечения (при увеличении экспоненты)
        if w_new > w_now:
            possible_ws.append(w_new)

    if not possible_ws:
        return None  # ни один кандидат не сможет обогнать лидера

    # Берём ближайшее пересечение
    w_min = max(min(min(possible_ws), 1.0), 0.0)

    # Переводим обратно в экспоненту
    exp_new = 1 + 19 * w_min

    return exp_new
