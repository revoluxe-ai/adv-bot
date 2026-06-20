"""ORM models for isolated free Rentgen access, invites, and shop bindings."""

from __future__ import annotations

import datetime
import typing

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.utils.db.base import BaseTable

if typing.TYPE_CHECKING:
    from app.utils.db.models import User


class RentgenInvite(BaseTable):
    """Invite code for granting access to the free Rentgen bot only."""

    __tablename__ = "rentgen_invite"

    code: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    max_uses: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )
    used_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    source: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
    )
    updated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    access_records: Mapped[list["RentgenAccess"]] = relationship(
        "RentgenAccess",
        back_populates="invite",
        uselist=True,
    )

    __table_args__ = (
        Index("ix_rentgen_invite_status", "status"),
    )


class RentgenAccess(BaseTable):
    """Separate access record ensuring free users stay outside the paid gate."""

    __tablename__ = "rentgen_access"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
        unique=True,
    )
    user: Mapped["User"] = relationship("User", uselist=False)
    invite_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("rentgen_invite.id"),
        nullable=True,
    )
    invite: Mapped[RentgenInvite | None] = relationship(
        "RentgenInvite",
        back_populates="access_records",
        uselist=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
    )
    activated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    blocked_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    source: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        Index("ix_rentgen_access_status", "status"),
    )


class RentgenShop(BaseTable):
    """Rentgen shop binding kept separate from paid runner activation state."""

    __tablename__ = "rentgen_shop"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id"),
        nullable=False,
    )
    wb_cabinet_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("wbcabinet.id"),
        nullable=True,
    )
    shop_id: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String,
        nullable=False,
        default="active",
        server_default=text("'active'"),
    )
    status_reason: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=text("now()"),
    )
    activated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    deactivated_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_eligibility_check_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_collect_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    last_snapshot_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )
    collect_interval_sec: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3600,
        server_default=text("3600"),
    )

    __table_args__ = (
        Index("ix_rentgen_shop_user_id", "user_id"),
        Index("ix_rentgen_shop_shop_id", "shop_id", unique=True),
        Index("ix_rentgen_shop_status", "status"),
    )
