import json
from dataclasses import dataclass
from typing import Union, Optional

from sqlalchemy import DateTime

from app.modules.keywords_query import keywords_query
from app.modules.common_slaves.wildberries.models import KeywordSetting


@dataclass
class KeywordStatus:
    VIEWS_IS_NOT_ENOUGH = "views_is_not_enough"
    MAX_CPC = 'max_cpc'
    GOOD = 'good'
    BAD = 'bad'



    @property
    def query(self):
        if self._query_static is None:
            return keywords_query.get_queries_of_keyword(self.text)
        else:
            return self._query_static

    @query.setter
    def query(self, value):
        self._query_static = value


    def __repr__(self):
        text = (f'text: {self.text}'
                f' clicks: {self.clicks}'
                f' views: {self.views}'
                f' spend: {self.spend}'
                f' status: {self.status}'
                f' keyword_setting: {self.keyword_setting}'
                f' cpc: {self.cpc}'
                f' ctr: {self.ctr}'
                f' hard_status: {self.hard_status}')
        return text


    @property
    def ctr(self):
        if self.views:
            return self.clicks / self.views
        return 0

    @property
    def cpc(self):
        clicks = self.clicks + 1
        return self.spend / clicks

    def to_json(self):
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str):
        return cls(**json.loads(json_str))
