from sqlalchemy import BIGINT, Table, Column, ForeignKey
from shared_lib.models.base_table import BaseTable

favorite_advs_association = Table(
    "favorite_advs_association",
    BaseTable.metadata,
    Column("user_id", BIGINT, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "adv_id",
        BIGINT,
        ForeignKey("advsetting.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
