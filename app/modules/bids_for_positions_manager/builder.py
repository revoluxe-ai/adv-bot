from .bids_for_positions_manager import BidsForPositionsManager
from .di import BidsForPositionsManagerContainer


def build_bids_for_positions_manager() -> BidsForPositionsManager:
    container = BidsForPositionsManagerContainer()
    return container.bids_for_positions_manager()
