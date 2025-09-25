from dataclasses import dataclass

from .update_bid_command import BidUpdateForNmidCommand


@dataclass
class UpdateBidsForAdvsCommand:
    shop_id: str
    update_nmids_commands: dict[int, list[BidUpdateForNmidCommand]]  # adv_id -> list of commands
