from typing import cast

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

    keywords_candidates: list[CalculatedKeyword] | None = get_candidates_to_leader(
        keywords
    )
    if not keywords_candidates:
        return None  # нет кандидатов
    # Текущий вес w (из диапазона [0, 1])
    w_now = (exponent_now - 1) / 19

    # Находим текущего лидера по рейтингу
    leader = get_leader(keywords_candidates)
    ctr_L, views_L = leader.predict_ctr, leader.views  # pyright: ignore

    # Отбираем кандидатов с CTR > CTR_лидера
    candidates = [
        kw
        for kw in keywords_candidates
        if kw.predict_ctr is not None and kw.predict_ctr > ctr_L  # pyright: ignore
    ]  # pyright: ignore
    if not candidates:
        return None  # нет кандидатов с большим CTR

    possible_ws: list[float] = []
    # TODO: Переделать CalculatedKeyword, чтобы не кастовать - привести все типы свойств в однозначные значения
    for cand in candidates:
        predict_ctr: float = cast(float, cand.predict_ctr)
        assert predict_ctr is not None
        views: int = cand.views
        assert views is not None
        ctr_i, views_i = predict_ctr, views
        numerator: float = ctr_L * views_L - ctr_i * views_i  # pyright: ignore
        denominator: float = ( # pyright: ignore
            ctr_i - ctr_i * views_i - ctr_L + ctr_L * views_L # pyright: ignore
        )  # pyright: ignore

        if denominator == 0:
            continue  # прямые параллельны, не пересекутся

        w_new: float = numerator / denominator  # pyright: ignore

        # Нас Интересует только будущие пересечения (при увеличении экспоненты)
        if w_new > w_now:
            possible_ws.append(w_new)  # pyright: ignore

    if not possible_ws:
        return None  # ни один кандидат не сможет обогнать лидера

    # Берём ближайшее пересечение
    w_min = max(min(min(possible_ws), 1.0), 0.0)

    # Переводим обратно в экспоненту
    exp_new = 1 + 19 * w_min

    return exp_new
