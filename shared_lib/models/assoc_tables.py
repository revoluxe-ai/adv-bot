from sqlalchemy import Table, Column, Integer, ForeignKey
from .base_table import Base

# Локальная association таблица для favorites между User и AdvSetting
favorite_advs_association = Table(
    "favorite_advs_association",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column("adv_id", Integer, ForeignKey("advsetting.id", ondelete="CASCADE"), primary_key=True),
)

