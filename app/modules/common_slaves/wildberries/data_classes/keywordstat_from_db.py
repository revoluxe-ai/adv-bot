import datetime
import json
from typing import Annotated
from typing import Any

from pydantic import BaseModel, PlainValidator

from app.modules.keywords_query import keywords_query


def validate_datetime(v: Any) -> datetime.datetime | None:
    if isinstance(v, datetime.datetime):
        return v
    if isinstance(v, str):
        return datetime.datetime.fromisoformat(v)
    if v is None:
        return None
    raise ValueError(f"Invalid datetime: {v}")


DatetimeType = Annotated[datetime.datetime, PlainValidator(validate_datetime)]


class KeywordStatus:
    GOOD = "good"
    BAD = "bad"
    VIEWS_IS_NOT_ENOUGH = "views_is_not_enough"
    MAX_CPM = "max_cpm"
    MAX_CPC = "max_cpc"


class CalculatedKeyword(BaseModel):
    text: str
    clicks: int
    views: int
    spend: float
    baes_ctr: float | None = None
    predict_ctr: float | None = None
    status: str | None = None
    hard_status: int | None = None
    reason: str | None = None
    _position: int | None = None
    position_update: DatetimeType | None = None
    childs_keywords: list["CalculatedKeyword"] | None = None
    _query_static: int | None = None
    cluster_name: str | None = None
    preset: int | None = None
    original_predict_ctr: float | None = None
    predict_ctr_exponent: float | None = None
    k: float | None = None
    best_keyword_status: bool | None = None
    baes_predict_ctr: float | None = None
    calculated_clicks: int | None = None
    calculated_views: int | None = None
    enough_views: int | None = None
    added_clicks: int | None = None
    keyword_setting_original_id: int | None = None
    adv_id: int | None = None
    relevant: bool | None = None
    _total_views: int | None = None

    @property
    def position(self) -> int | None:
        return self._position

    @position.setter
    def position(self, value: int | None) -> None:
        assert isinstance(value, (int, None))
        self._position = value

    @property
    def total_views(self) -> int | None:
        return self._total_views

    @total_views.setter
    def total_views(self, value: int | None) -> None:
        assert isinstance(value, int | None)
        self._total_views = value

    def clear_cache(self):
        """Очистка кэшированных свойств"""
        for attr in ["_query_static", "_mean_ctr_cache", "_rating_cache"]:
            if hasattr(self, attr):
                delattr(self, attr)

    @property
    def mean_ctr(self):
        assert self.predict_ctr is not None
        assert self.baes_ctr is not None
        return (self.predict_ctr + self.baes_ctr) / 2

    # TODO: Была ошибка в проде: с ростом экспоненты рейтинг падал. Исправлено. Сделать тесты
    @property
    def rating_by_predict_ctr(self) -> float:
        """Линейный баланс между CTR×views и CTR по экспоненте (1–20)."""
        if self.predict_ctr is None or self.predict_ctr_exponent is None:
            return 0.0
        ctr = min(max(self.predict_ctr, 0.0), 1.0)
        views = max(self.views or 0.0, 0.0)
        w = (self.predict_ctr_exponent - 1) / 19
        w = min(max(w, 0.0), 1.0)

        # линейный переход от CTR×views → CTR
        traffic_component = ctr * views
        rating = (1 - w) * traffic_component + w * ctr
        return rating

    @property
    def query(self) -> int | str:
        if self._query_static is None:
            return keywords_query.get_queries_of_keyword(self.text)
        else:
            return self._query_static

    @query.setter
    def query(self, value: int | str):
        self._query_static = value

    def __repr__(self) -> str:
        text = (
            f"text: {self.text}"
            f" clicks: {self.clicks}"
            f" views: {self.views}"
            f" spend: {self.spend}"
            f" status: {self.status}"
            f" cpc: {self.cpc}"
            f" ctr: {self.ctr}"
            f" hard_status: {self.hard_status}"
        )
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
            "text": self.text,
            "clicks": self.clicks,
            "views": self.views,
            "spend": self.spend,
            "base_ctr": self.baes_ctr,
            "predict_ctr": self.predict_ctr,
            "status": self.status,
            "hard_status": self.hard_status,
            "reason": self.reason,
            "position": self.position,
            "position_update": (
                self.position_update.isoformat() if self.position_update else None
            ),
            "query_static": self._query_static,
            "cluster_name": self.cluster_name,
            "preset": self.preset,
            "original_predict_ctr": self.original_predict_ctr,
            "predict_ctr_exponent": self.predict_ctr_exponent,
            "k": self.k,
            "best_keyword_status": self.best_keyword_status,
            "baes_predict_ctr": self.baes_predict_ctr,
            "calculated_clicks": self.calculated_clicks,
            "calculated_views": self.calculated_views,
            "enough_views": self.enough_views,
        }
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "CalculatedKeyword":
        data = json.loads(json_str)
        data["position_update"] = (
            validate_datetime(data["position_update"])
            if data["position_update"]
            else None
        )
        # Backward compatibility
        # 1) Map real_position -> position if no position
        if "position" not in data and "real_position" in data:
            data["position"] = data.get("real_position")
        # 2) If position is a dict (legacy WBItemPosition), extract integer
        if isinstance(data.get("position"), dict):
            legacy = data["position"]
            data["position"] = (
                legacy.get("position")
                or legacy.get("real_position")
                or legacy.get("base_position")
                or legacy.get("promo_position")
                or 0
            )
        return cls(**data)

    @property
    def is_in_white_list(self) -> bool:
        return self.hard_status == 2
