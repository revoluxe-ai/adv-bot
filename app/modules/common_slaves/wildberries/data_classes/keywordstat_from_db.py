from dataclasses import dataclass
from typing import Union
from app.modules.common_slaves.wildberries.models import KeywordSetting


@dataclass
class KeywordStatFromDB:
    text: str
    clicks: int
    views: int
    spend: float
    status: Union[str, None] = None
    keyword_setting: Union[KeywordSetting, None] = None

    @property
    def ctr(self):
        if self.views:
            return self.clicks / self.views
        return 0
