from sqlalchemy import BIGINT, Column, String, UniqueConstraint
from sqlalchemy.orm import Mapped

from app.utils.db.base import BaseTable


class TelegramFile(BaseTable):
    file_telegram_id: Mapped[int] = Column(String, unique=True, nullable=False)
    dhash: Mapped[str] = Column(String, nullable=False)
    bot_id: Mapped[int] = Column(BIGINT, nullable=False)
    __table_args__ = (UniqueConstraint("bot_id", "dhash", name="_bot_id_dhash_uc"),)
