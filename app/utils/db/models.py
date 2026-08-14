__all__ = (
    "User",
    "Payment",
    "UserBalancePayment",
    "UserBonusPayment",
    "PartnerPayout",
    "PassedGateReason",
    "InviteStatus",
    "Invite",
)

import datetime
import enum
import typing

from sqlalchemy import (
    BIGINT,
    Boolean,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db.passed_gate_reason import PassedGateReason


class InviteStatus(str, enum.Enum):
    """Статус инвайта."""

    ACTIVE = "ACTIVE"
    USED = "USED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


if typing.TYPE_CHECKING:
    from app.modules.common_slaves.wildberries.models import (
        AdvSetting,
        WBToken,
        WBUserCabinet,
    )
from app.payments.db.models import Payment
from app.utils.db.assoc_tables import favorite_advs_association
from app.utils.db.base import BaseTable


class User(BaseTable):
    # TODO Модель расшарена, отрефакторить перед изменениями
    user_telegram_id: Mapped[int | None] = mapped_column(
        BIGINT, nullable=True, unique=True
    )
    username: Mapped[str] = mapped_column(String, nullable=True)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    # Web registration (phase 1: nullable; phase 2 may tighten to NOT NULL/UNIQUE)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    wb_user_cabinets: Mapped[list["WBUserCabinet"]] = relationship(
        "WBUserCabinet", back_populates="user", cascade="all, delete-orphan"
    )
    adv_updater_user_chat_id: Mapped[int] = mapped_column(BIGINT, nullable=True)
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
        "UserBonusPayment",
        back_populates="user",
        uselist=True,
        foreign_keys="UserBonusPayment.user_id",
    )
    partner_payouts_received: Mapped[list["PartnerPayout"]] = relationship(
        "PartnerPayout",
        back_populates="partner_user",
        uselist=True,
        foreign_keys="PartnerPayout.partner_user_id",
    )
    partner_payouts_created: Mapped[list["PartnerPayout"]] = relationship(
        "PartnerPayout",
        back_populates="created_by_admin_user",
        uselist=True,
        foreign_keys="PartnerPayout.created_by_admin_user_id",
    )
    passed_gate: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    passed_gate_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    passed_gate_reason: Mapped[PassedGateReason | None] = mapped_column(
        SAEnum(PassedGateReason), nullable=True
    )
    last_invite_issued_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    __table_args__ = (Index("user_telegram_id_index", user_telegram_id),)


class UserBalancePayment(BaseTable):
    """Запись о пополнении/списании личного баланса пользователя."""

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

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="user_bonus_payments",
        foreign_keys=[user_id],
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    transaction_date_time: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    operation_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'add'")
    )
    admin_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )

    __table_args__ = (
        Index("idx_user_bonus_payment_user_id", "user_id"),
        Index("idx_user_bonus_payment_date", "transaction_date_time"),
        Index("idx_user_bonus_payment_admin", "admin_user_id"),
        Index("idx_user_bonus_payment_operation", "operation_type"),
    )


class PartnerPayout(BaseTable):
    """Запись факта выплаты партнёру по партнёрской программе."""

    # BaseTable задаёт __tablename__ через @declared_attr; строковый override
    # сохраняет физическое имя partner_payout (не partnerpayout).
    # @declared_attr.directive несовместим с типом родителя (pyright).
    __tablename__ = "partner_payout"  # pyright: ignore[reportAssignmentType]

    partner_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    partner_user: Mapped["User"] = relationship(
        "User",
        back_populates="partner_payouts_received",
        foreign_keys=[partner_user_id],
    )

    amount: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, nullable=False, server_default=text("now()")
    )
    created_by_admin_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=False
    )
    created_by_admin_user: Mapped["User"] = relationship(
        "User",
        back_populates="partner_payouts_created",
        foreign_keys=[created_by_admin_user_id],
    )
    comment: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("idx_partner_payout_partner_user_id", "partner_user_id"),
        Index(
            "idx_partner_payout_created_by_admin_user_id",
            "created_by_admin_user_id",
        ),
        Index("idx_partner_payout_created_at", "created_at"),
    )


class Invite(BaseTable):
    """Инвайт-код для прохождения гейта или выдачи пользователю (invite:show)."""
    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    issued_to_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )
    issued_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        SAEnum(InviteStatus), nullable=False, default=InviteStatus.ACTIVE
    )
    used_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id"), nullable=True
    )
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (Index("ix_invites_code", "code", unique=True),)
