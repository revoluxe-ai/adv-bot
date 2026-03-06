from enum import StrEnum, auto


class KeywordStatusReason(StrEnum):
    BIDDER_BAD_STATUS = auto()
    MAX_POSITION = auto()
    BLACK_LIST = "black_list"
    WHITE_LIST = "white_list"
    TURN_OFF = "turn_off"
    ALWAYS_ON = "always_on"
    MORE_THEN_HARD_MIN_CTR = auto()
    LESS_THEN_HARD_MIN_CTR = auto()
    MAX_CPM = "max_cpm"
    MAX_CPC = "max_cpc"
    MORE_THEN_RATING_BY_ORDERS = auto()
    LESS_THEN_RATING_BY_ORDERS = auto()
    BELOW_REC_CONVERSION = auto()
    WB_MIN_BID_TOO_HIGH = "wb_min_bid_too_high"
    BEST_KEYWORD = auto()
    NOT_RELEVANT_PHRASE = auto()
    RATING_IS_NONE = auto()

class KeywordStatus(StrEnum):
    GOOD = "good"
    BAD = "bad"
    VIEWS_IS_NOT_ENOUGH = "views_is_not_enough"
