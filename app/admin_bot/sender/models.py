from sqlalchemy.orm import Mapped
from app.utils.db.base import BaseTable
from sqlalchemy import Column, BIGINT, String


class TelegramFile(BaseTable):
    file_telegram_id: Mapped[int] = Column(BIGINT, unique=True, nullable=False)
    dhash = Mapped[str] = Column(String, unique=True, nullable=False)