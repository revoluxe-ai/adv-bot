__all__ = (
    "User",
    "RefLink",
    "user_reflink_association",
    "Payment",
    "UserBalancePayment",
    "UserBonusPayment",
)

import datetime
import typing

from sqlalchemy import (
    BIGINT,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import (
        AdvSetting,
        WBToken,
        WBUserCabinet,
    )
from app.payments.db.models import Payment
from app.utils.db.assoc_tables import (
    favorite_advs_association,
    user_reflink_association,
)
from app.utils.db.base import BaseTable


class User(BaseTable):
    # TODO Модель расшарена, отрефакторить перед изменениями
    user_telegram_id: Mapped[int] = mapped_column(BIGINT, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String, nullable=True)
    wb_user_cabinets: Mapped[list["WBUserCabinet"]] = relationship(
        "WBUserCabinet", back_populates="user", cascade="all, delete-orphan"
    )
    adv_updater_user_chat_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
    referral_links: Mapped[list["RefLink"]] = relationship(
        "RefLink", back_populates="referrer", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
    wb_tokens: Mapped[list["WBToken"]] = relationship(
        "WBToken", back_populates="user", cascade="all, delete-orphan"
    )
    favorites_advs: Mapped[list["AdvSetting"]] = relationship(
        "AdvSetting", secondary=favorite_advs_association
    )
    user_balance_payments: Mapped[list["UserBalancePayment"]] = relationship(
        "UserBalancePayment", back_populates="user", uselist=True
    )
    user_bonus_payments: Mapped[list["UserBonusPayment"]] = relationship(
        "UserBonusPayment", back_populates="user", uselist=True
    )
    __table_args__ = (Index("user_telegram_id_index", user_telegram_id),)


class UserBalancePayment(BaseTable):
    """Запись о пополнении/списании личного баланса пользователя."""

    __tablename__ = "userbalancepayment"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="user_balance_payments")

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'add'")
    )
    __table_args__ = (
        Index("idx_user_balance_payment_user_id", "user_id"),
        Index("idx_user_balance_payment_date", "transaction_date_time"),
        Index("idx_user_balance_payment_operation", "operation_type"),
    )


class UserBonusPayment(BaseTable):
    """Запись о начислении/списании бонусов пользователя."""

    __tablename__ = "userbonuspayment"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    user: Mapped["User"] = relationship("User", back_populates="user_bonus_payments")

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'add'")
    )
    admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_user_bonus_payment_user_id", "user_id"),
        Index("idx_user_bonus_payment_date", "transaction_date_time"),
        Index("idx_user_bonus_payment_admin", "admin_user_id"),
        Index("idx_user_bonus_payment_operation", "operation_type"),
    )


class RefLink(BaseTable):
    name = Column(String, nullable=False)
    referrer_id = Column(BIGINT, ForeignKey("user.id"))
    referrer: Mapped["User"] = relationship("User", back_populates="referral_links")
    referred_users: Mapped[list["User"]] = relationship(
        "User", secondary=user_reflink_association, backref="referred_by_links"
    )
    created_at = Column(DateTime, server_default=func.now())
