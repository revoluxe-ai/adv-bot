from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)
from .utils import get_candidates_to_leader, get_leader


def get_next_down_exponent(
    exponent_now: float, keywords: list["CalculatedKeyword"]
) -> float | None:
    """
    Вычисляет новое минимальное значение экспоненты exp_new < exp_now,
    при котором появится новый лидер (при снижении exp).
    Если даже при exp = 1 лидер остаётся тем же — возвращает None.

    :param exponent_now: текущая экспонента (1–20)
    :param keywords: список ключей с полями:
                     - predict_ctr
                     - views
                     - rating_by_predict_ctr (текущий рейтинг)
    :return: новое значение экспоненты exp_new или None
    """

    # TODO: Кажется эту функцию можно частично слить с get_next_up_exponent

    keywords_candidates: list[CalculatedKeyword] | None = get_candidates_to_leader(
        keywords
    )
    if not keywords_candidates:
        return None

    # 1️⃣ текущий вес
    w_now = (exponent_now - 1) / 19

    # 2️⃣ текущий лидер
    leader = get_leader(keywords_candidates)
    if not leader:
        return None
    ctr_L, views_L = leader.predict_ctr, leader.views

    possible_ws: list[float] = []

    # 3️⃣ считаем все точки пересечения
    for cand in keywords:
        if cand is leader:
            continue

        ctr_i, views_i = cand.predict_ctr, cand.views
        numerator: float = ctr_L * views_L - ctr_i * views_i  # pyright: ignore
        denominator: float = ( # pyright: ignore
            ctr_i - ctr_i * views_i - ctr_L + ctr_L * views_L # pyright: ignore
        )  # pyright: ignore

        if denominator == 0:
            continue  # прямые параллельны

        w_new: float = numerator / denominator  # pyright: ignore

        # интересуют пересечения при снижении экспоненты
        if 0 <= w_new < w_now:
            possible_ws.append(w_new)  # pyright: ignore

    # 4️⃣ если нет пересечений — проверим exp=1
    if not possible_ws:
        # Посчитаем рейтинги при exp=1 (w=0)
        for kw in keywords_candidates:
            kw._tmp_rating = kw.predict_ctr * kw.views  # type: ignore[attr-defined]
        new_leader = max(keywords_candidates, key=lambda k: k._tmp_rating)  # type: ignore[attr-defined]
        if new_leader is leader:
            return None  # даже при exp=1 лидер не меняется
        else:
            return 1.0  # лидер сменился только при самом минимуме

    # 5️⃣ выбираем ближайшее пересечение "вниз"
    w_min = max(possible_ws)

    # 6️⃣ переводим обратно в экспоненту
    exp_new = 1 + 19 * w_min
    exp_new = max(min(exp_new, 20.0), 1.0)

    return round(exp_new, 6)
