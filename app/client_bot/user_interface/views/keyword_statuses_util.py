from app.modules.wb_adv_updater.calculated_keywords_manager.dto.calculated_keyword import CalculatedKeyword
from app.modules.wb_adv_updater.calculated_keywords_manager.dto.states import KeywordStatusReason


def get_hard_status(keyword: CalculatedKeyword) -> str:
    if keyword.hard_status == 0:
        return 'НРФ'
    if keyword.hard_status == 1:
        return 'А'
    if keyword.hard_status == 2:
        return 'БС'
    if keyword.hard_status == 3:
        return 'O'
    else:
        raise ValueError(f"Unknown hard_status: {keyword.hard_status}")


def get_dynamic_status(keyword: CalculatedKeyword) -> str:
    reason = keyword.reason
    if reason == KeywordStatusReason.BIDDER_BAD_STATUS:
        status = '(Б)'
    elif reason == KeywordStatusReason.MAX_CPC:
        status = '(МС)'
    elif reason == KeywordStatusReason.MORE_THEN_HARD_MIN_CTR:
        status = '(ВР)'
    elif reason == KeywordStatusReason.LESS_THEN_RATING_BY_ORDERS:
        status = "(НР)"
    elif reason == KeywordStatusReason.WHITE_LIST:
        status = ""
    elif reason == KeywordStatusReason.MAX_POSITION:
        status = "(ЦП)"
    else:
        status = ""
    return status





