from sqlalchemy import Integer, String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base_table import BaseTable

class KeywordSetting(BaseTable):
    # Минимальное представление модели, достаточное для запросов в data_manager
    text: Mapped[str] = mapped_column(String, nullable=False)
    hard_status: Mapped[int] = mapped_column(Integer, default=1)
    adv_setting_id: Mapped[int] = mapped_column(Integer, ForeignKey("advsetting.id"), nullable=False)

