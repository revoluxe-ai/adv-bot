from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import (
    CalculatedKeyword,
)


def get_candidates_to_leader(
    keywords: list[CalculatedKeyword],
) -> list[CalculatedKeyword] | None:
    def filter_func(keyword: CalculatedKeyword) -> bool:
        return all([keyword.relevant])

    return list(filter(filter_func, keywords))


def get_leader(keywords: list[CalculatedKeyword]) -> CalculatedKeyword | None:
    def filter_func(keyword: CalculatedKeyword) -> bool:
        return all(
            [
                keyword.hard_status == 2,
            ]
        )

    candidates = list(filter(filter_func, keywords))
    if not candidates:
        return None
    return max(candidates, key=lambda kw: kw.rating_by_predict_ctr)
