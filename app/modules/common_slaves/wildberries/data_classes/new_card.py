from wb.cards_manager_old.barcode_handler import BarcodeHandler
from wb.cards_manager_old.drivers import WbNeo4j

from .card_from_disc import CardFromDisc


class NewCard(CardFromDisc):
    def __init__(self, path, barcode_run =  True):
        super().__init__(path)
        self._neo4j = WbNeo4j()
        self._update_data()
        self._barcode = barcode_run
        self._nmid = None

    @property
    def nmid(self):
        return self._nmid

    @nmid.setter
    def nmid(self, value):
        self._nmid  = value


    def _update_data(self):
        self.__get_offer_id()
        self.__get_barcode()



    def __get_barcode(self, barcode_run = True):
        bh = BarcodeHandler(barcode_run = barcode_run)
        barcode = bh.get_barcode()
        self._wb_barcode = barcode


    def __get_offer_id(self):
        next_offer_id = self._neo4j.generate_new_offer_id(self.prefix)
        self.offer_id = next_offer_id
