from sqlalchemy import BIGINT, Column, ForeignKey, Table

from app.utils.db.base import Base

favorite_advs_association = Table(
    "favorite_advs_association",
    Base.metadata,
    Column(
        "user_id", BIGINT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "adv_id",
        BIGINT,
        ForeignKey("advsetting.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
