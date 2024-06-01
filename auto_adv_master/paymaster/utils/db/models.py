from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import Mapped

from auto_adv_master.modules.common_slaves.wildberries.models import WBCabinet
from auto_adv_master.utils.db.base import BaseTable
from auto_adv_master.utils.db.models import User


class Payment(BaseTable):
    id: Mapped[int] = Column(Integer, primary_key=True)
    amount: Mapped[int] = Column(Integer, nullable=False)
    coin_amount: Mapped[int] = Column(Integer, nullable=False)
    user: Mapped[User] = ForeignKey('User', nullable=False)
    user_id: Mapped[int] = Column(Integer, ForeignKey('user.id'), nullable=False)
    wb_cabinet: Mapped[WBCabinet] = ForeignKey('WBCabinet', nullable=False)
    wb_cabinet_id = Column(Integer, ForeignKey('wbcabinet.id'), nullable=False)
    ...

