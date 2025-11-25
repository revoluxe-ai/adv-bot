import datetime
import json
from typing import Annotated
from typing import Any

from pydantic import BaseModel, PlainValidator

from app.modules.common_slaves.wildberries.models import WBItemPosition
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


def _parse_position_value(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.isdigit():
            return int(cleaned)
        try:
            return int(float(cleaned))
        except ValueError:
            return None
    return None


class KeywordStatus:
    GOOD = "good"
    BAD = "bad"
    VIEWS_IS_NOT_ENOUGH = "views_is_not_enough"
    MAX_CPM = "max_cpm"
    MAX_CPC = "max_cpc"


class CalculatedKeyword(BaseModel):
    # TODO: Разобраться с сериализацией-десериализацией
    text: str
    clicks: int
    views: int
    spend: float
    baes_ctr: float | None = None
    predict_ctr: float | None = None
    status: str | None = None
    hard_status: int | None = None
    reason: str | None = None
    _position: WBItemPosition | None = None
    childs_keywords: list["CalculatedKeyword"] | None = None
    _query_static: int | str | None = None
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

    @property
    def position_update(self) -> datetime.datetime | None:
        if self._position is None:
            return None
        return self._position.timestamp

    @property
    def position(self) -> int | None:
        if not self._position:
            return None
        return self._position.position

    @position.setter
    def position(self, value: WBItemPosition) -> None:
        assert isinstance(value, WBItemPosition)
        self._position = value


    @property
    def total_views(self) -> int | None:
        if not self._position:
            return None
        return self._position.total_views

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
        raw_position: Any = data.pop("position", None)
        raw_position_update = data.pop("position_update", None)
        position_update = (
            validate_datetime(raw_position_update) if raw_position_update else None
        )

        if raw_position is None and "real_position" in data:
            raw_position = data.get("real_position")
        elif raw_position is None:
            for fallback in ("base_position", "promo_position"):
                if fallback in data:
                    raw_position = data.get(fallback)
                    break
        # TODO: не тестировалось, надо пересмотреть - перепроверить
        position_model: WBItemPosition | None = None
        if isinstance(raw_position, dict):
            position_model = WBItemPosition.from_dict(raw_position) # pyright: ignore
        else:
            normalized_position = _parse_position_value(raw_position)
            if normalized_position is not None:
                position_model = WBItemPosition(position=normalized_position)

        if position_model and position_update:
            position_model.timestamp = position_update
        elif position_model is None and position_update:
            position_model = WBItemPosition(timestamp=position_update)

        if position_model and not position_model.keyword_text:
            keyword_text = data.get("text")
            if isinstance(keyword_text, str):
                position_model.keyword_text = keyword_text

        instance = cls(**data)
        if position_model:
            instance.position = position_model
        return instance

    @property
    def is_in_white_list(self) -> bool:
        return self.hard_status == 2
