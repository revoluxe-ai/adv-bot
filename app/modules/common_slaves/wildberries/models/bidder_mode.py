from enum import Enum, auto


class BidderMode(Enum):
    BY_AUTO_MAX_CPM = auto()
    BY_POSITIONS = auto()