from .abc_card import CardGroupABC
from .card_from_neo4j import CardFromDB
from .card_from_wb import CardFromWB
from collections import defaultdict as dd
from .abc_card import WBCard
from typing import List, Dict




class CardGroup(CardGroupABC):
    def __init__(self, group: List[CardFromDB], offer_id_to_card: Dict[str, CardFromWB]):

        self._offer_id_to_card  = offer_id_to_card
        target_card = group.pop()
        wb_card = offer_id_to_card[target_card.offer_id]
        self._targetIMT = wb_card.imtID
        self._cards= group

    def __eq__(self, other:CardGroupABC):
        if isinstance(other, CardGroupABC):
            return self.targetIMT == other.targetIMT \
                and self.json == other.json
        return False



    @property
    def targetIMT(self):
        return self._targetIMT


    @property
    def nmIDs(self):
        nmids = []
        for card in self._cards:
            offer_id = card.offer_id
            if offer_id in self._offer_id_to_card:
                wb_card = self._offer_id_to_card[card.offer_id]
                nmids.append(wb_card.nmid)
        return nmids




    @property
    def json(self):
        return {
            "targetIMT": self.targetIMT,
            "nmIDs": self.nmIDs
        }


    @property
    def json_unglue(self):
        return {
            "nmIDs": self.nmIDs
        }




