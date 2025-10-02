# Модель CalculatedKeyword перенесена из app/modules/common_slaves/wildberries/data_classes/keywordstat_from_db.py
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CalculatedKeyword(BaseModel):
    text: str
    clicks: int
    views: int
    spend: float
    baes_ctr: Optional[float] = None
    predict_ctr: Optional[float] = None
    status: Optional[str] = None
    hard_status: Optional[int] = None
    reason: Optional[str] = None
    position: Optional[int] = None
    position_update: Optional[datetime] = None
    childs_keywords: Optional[List["CalculatedKeyword"]] = None
    _query_static: Optional[int] = None
    cluster_name: Optional[str] = None
    preset: Optional[int] = None
    original_predict_ctr: Optional[float] = None
    predict_ctr_exponent: Optional[float] = None
    k: Optional[float] = None
    best_keyword_status: Optional[bool] = None
    baes_predict_ctr: Optional[float] = None
    calculated_clicks: Optional[int] = None
    calculated_views: Optional[int] = None
    enough_views: Optional[int] = None
    added_clicks: Optional[int] = None
    keyword_setting_original_id: Optional[int] = None
    adv_id: Optional[int] = None
    relevant: Optional[bool] = None

    def clear_cache(self):
        for attr in ["_query_static", "_mean_ctr_cache", "_rating_cache"]:
            if hasattr(self, attr):
                delattr(self, attr)

    @property
    def mean_ctr(self):
        assert self.predict_ctr is not None
        assert self.baes_ctr is not None
        return (self.predict_ctr + self.baes_ctr) / 2

    @property
    def rating_by_predict_ctr(self) -> float:
        predict_ctr_exponent: float = self.predict_ctr_exponent
        rating = self.predict_ctr**predict_ctr_exponent * self.views
        return rating

