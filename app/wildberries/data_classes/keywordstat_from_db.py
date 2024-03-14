from dataclasses import dataclass

from app.wildberries.models import KeywordSetting


@dataclass
class KeywordStatFromDB:
    text: str
    clicks: int
    views: int
    spend: float

    @property
    def ctr(self):
        if self.views:
            return self.clicks / self.views
        return 0
