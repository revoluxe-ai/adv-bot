import datetime
from typing import Optional, Union, List, Any, Callable
import math
import json
from typing_extensions import Annotated
from pydantic import BaseModel, Field, field_validator, PlainValidator
from app.modules.common_slaves.wildberries.models import KeywordSetting, WBItemPosition
from app.modules.keywords_query import keywords_query


def validate_datetime(v: Any) -> datetime.datetime:
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, str):
        return datetime.datetime.fromisoformat(v)
    if v is None:
        return None
    raise ValueError(f'Invalid datetime: {v}')


DatetimeType = Annotated[datetime.datetime, PlainValidator(validate_datetime)]


class KeywordStatus:
    GOOD = 'good'
    BAD = 'bad'
    VIEWS_IS_NOT_ENOUGH = 'views_is_not_enough'


class CalculatedKeyword(BaseModel):
    model_config = {
        "arbitrary_types_allowed": True
    }
    
    text: str
    clicks: int
    views: int
    spend: float
    baes_ctr: Optional[float] = None
    predict_ctr: Optional[float] = None
    status: Union[str, None] = None
    hard_status: Union[str, None] = None
    reason: Optional[str] = None
    cpm: Optional[int] = None
    real_position: Optional[int] = None
    base_position: Optional[int] = None
    promo_position: Optional[int] = None
    position_update: Optional[DatetimeType] = None
    childs_keywords: Optional[List['CalculatedKeyword']] = None
    _query_static: Optional[int] = None
    cluster_name: Optional[str] = None
    preset: Optional[int] = None
    position: Optional[WBItemPosition] = None
    original_predict_ctr: Optional[float] = None
    predict_ctr_exponent: Optional[float] = None
    k: Optional[float] = None
    best_keyword_status: Optional[bool] = None
    baes_predict_ctr: Optional[float] = None
    calculated_clicks: Optional[int] = None
    calculated_views: Optional[int] = None
    enough_views: Optional[int] = None
    added_clicks: Optional[int] = None
    keyword_setting_original_id: int | None = None

    @property
    def mean_ctr(self):
        return (self.predict_ctr + self.baes_ctr) / 2

    @property
    def rating_by_predict_ctr(self) -> float:
        k = 1
        predict_ctr_exponent = self.predict_ctr_exponent
        if not self.base_position:
            return 0
        if self.predict_ctr is None:
            return 0
        rating = self.predict_ctr ** predict_ctr_exponent * self.views / (k * math.log(1 + self.base_position))
        return rating

    @property
    def query(self) -> Union[int, str]:
        if self._query_static is None:
            return keywords_query.get_queries_of_keyword(self.text)
        else:
            return self._query_static

    @query.setter
    def query(self, value: Union[int, str]):
        self._query_static = value

    def __repr__(self) -> str:
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
    def ctr(self) -> float:
        if self.views:
            return self.clicks / self.views
        return 0

    @property
    def cpc(self) -> float:
        clicks = self.clicks + 1
        return self.spend / clicks

    def to_json(self) -> str:
        data = {
            'text': self.text,
            'clicks': self.clicks,
            'views': self.views,
            'spend': self.spend,
            'base_ctr': self.baes_ctr,
            'predict_ctr': self.predict_ctr,
            'status': self.status,
            'hard_status': self.hard_status,
            'reason': self.reason,
            'cpm': self.cpm,
            'real_position': self.real_position,
            'base_position': self.base_position,
            'promo_position': self.promo_position,
            'position_update': self.position_update.isoformat() if self.position_update else None,
            'childs_keywords': [k.to_json() for k in self.childs_keywords] if self.childs_keywords else None,
            'query_static': self._query_static,
            'cluster_name': self.cluster_name,
            'preset': self.preset,
            'position': self.position.to_dict() if self.position else None,
            'original_predict_ctr': self.original_predict_ctr,
            'predict_ctr_exponent': self.predict_ctr_exponent,
            'k': self.k,
            'best_keyword_status': self.best_keyword_status,
            'baes_predict_ctr': self.baes_predict_ctr,
            'calculated_clicks': self.calculated_clicks,
            'calculated_views': self.calculated_views,
            'enough_views': self.enough_views,
        }
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'CalculatedKeyword':
        data = json.loads(json_str)
        data['position_update'] = validate_datetime(data['position_update']) if data['position_update'] else None
        data['childs_keywords'] = [CalculatedKeyword.from_json(k) for k in data['childs_keywords']]\
            if data['childs_keywords'] else None
        data['position'] = WBItemPosition.from_dict(data['position']) if data['position'] else None
        return cls(**data)
