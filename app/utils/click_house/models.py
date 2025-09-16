from clickhouse_sqlalchemy.types import DateTime, Float, Int32, String
from sqlalchemy import Column, UniqueConstraint

from .base import BaseTable


class AdvKeyword(BaseTable):
    text = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    views = Column(Int32, default=0)
    clicks = Column(Int32, default=0)
    spend = Column(Float, default=0)
    adv_id = Column(Int32, nullable=True)
    __table_args__ = (
        UniqueConstraint("text", "date", "adv_id", name="_text_date_adv_id_uc"),
    )
