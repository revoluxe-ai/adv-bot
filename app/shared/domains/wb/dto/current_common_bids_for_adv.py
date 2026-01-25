


class CurrentCommonBidsForAdv:
    def __init__(self, adv_id_of_wb_adv: int, nmids_to_bids: dict[int, int]):
        self._adv_id_of_wb_adv = adv_id_of_wb_adv
        self._nmids_to_bids = nmids_to_bids


    def __get_item__(self, nmid: int) -> int:
        return self._nmids_to_bids[nmid]

    @property
    def adv_id(self) -> int:
        return self._adv_id_of_wb_adv
