from app.modules.common_slaves.wildberries.data_classes.keywordstat_from_db import CalculatedKeyword
from app.modules.common_slaves.wildberries.models import AdvSetting


class KeywordsParser:
    def __init__(self,  parsing_queue_dict: dict[str, set],
                 shop_id: str,
                 adv: AdvSetting,
                 keywords: list[CalculatedKeyword],
                 ):
        self._parsing_queue_dict = parsing_queue_dict
        self.__target_nmids = set(adv.nmids)
        self.__keywords = keywords
        self._adv = adv

    def create_tasks_for_keywords_parser(self, ):
        parsing_queue_dict = self._parsing_queue_dict
        nmids = self.__target_nmids
        for kw in self.__keywords:
            text = kw.text
            for nmid in nmids:
                if not text in parsing_queue_dict:
                    parsing_queue_dict[text] = set()
                parsing_queue_dict[text].add(nmid)










