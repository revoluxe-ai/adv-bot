import json
import math
from dataclasses import dataclass
from typing import Union, Optional

from sqlalchemy import DateTime

from app.modules.keywords_query import keywords_query
from app.modules.common_slaves.wildberries.models import KeywordSetting, WBItemPosition


@dataclass
class KeywordStatus:
    VIEWS_IS_NOT_ENOUGH = "views_is_not_enough"
    MAX_CPC = 'max_cpc'
    GOOD = 'good'
    BAD = 'bad'


@dataclass
class CalculatedKeyword:
    text: str
    clicks: int
    views: int
    spend: float
    baes_ctr: Optional[float] = None
    predict_ctr: Optional[float] = None
    status: Union[str, None] = None
    keyword_setting: Union[KeywordSetting, None] = None
    hard_status: Union[str, None] = None
    reason: Optional[str] = None
    cpm: Optional[int] = None
    real_position: Optional[int] = None
    base_position: Optional[int] = None
    promo_position: Optional[int] = None
    position_update: Optional[DateTime] = None
    childs_keywords: Optional[list] = None
    _query_static: Optional[int] = None
    cluster_name: Optional[str] = None
    preset: Optional[int] = None
    position: Optional[WBItemPosition] = None
    original_predict_ctr: Optional[float] = None
    predict_ctr_exponent: Optional[float] = None
    k: Optional[float] = None
    best_keyword_status: [bool] = None

    @property
    def mean_ctr(self):
        return (self.predict_ctr + self.baes_ctr)/2


    @property
    def rating_by_predict_ctr(self):
        k = 1
        predict_ctr_exponent = self.predict_ctr_exponent
        if not self.base_position:
            return 0
        if self.predict_ctr is None:
            return 0
        rating = self.predict_ctr ** predict_ctr_exponent * self.views / (k * math.log(1 + self.base_position))
        return rating

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
