import json
from dataclasses import dataclass
from typing import Union
from app.modules.common_slaves.wildberries.models import KeywordSetting


@dataclass
class KeywordStatus:
    MAX_CPC = 'max_cpc'
    GOOD = 'good'
    BAD = 'bad'


@dataclass
class CalculatedKeyword:
    text: str
    clicks: int
    views: int
    spend: float
    status: Union[str, None] = None
    keyword_setting: Union[KeywordSetting, None] = None
    hard_status: Union[str, None] = None
    bad_reason: Union[str, None] = None

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
