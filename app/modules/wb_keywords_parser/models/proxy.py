"""SQLAlchemy model representing parser proxies for Wildberries keyword parsing."""

from __future__ import annotations

import datetime as dt
from typing import Optional, Tuple

from sqlalchemy import Boolean, DateTime, Integer, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.db.base import BaseTable


class ParserProxy(BaseTable):
    """Proxy configuration used by the Wildberries keywords parser."""

    __tablename__ = "parser_proxy"

    scheme: Mapped[str] = mapped_column(
        String(length=16), nullable=False, server_default=text("'http'"), index=True
    )
    host: Mapped[str] = mapped_column(String(length=255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(length=255), nullable=True)
    password: Mapped[Optional[str]] = mapped_column(String(length=255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true"), index=True
    )
    last_used_at: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )
    fail_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0"), index=True
    )
    cooldown_until: Mapped[Optional[dt.datetime]] = mapped_column(
        DateTime, nullable=True, index=True
    )

    __table_args__ = (
        UniqueConstraint("host", "port", name="uq_parser_proxy_host_port"),
    )

    @property
    def aiohttp_proxy(self) -> Tuple[str, Optional[Tuple[str, str]]]:
        """Return the proxy URL and optional authentication tuple for aiohttp."""

        proxy_url = f"{self.scheme}://{self.host}:{self.port}"
        if self.username is None:
            return proxy_url, None

        return proxy_url, (self.username, self.password or "")

    def mark_used(self, *, timestamp: Optional[dt.datetime] = None) -> None:
        """Convenience helper for updating the last used timestamp."""

        self.last_used_at = timestamp or dt.datetime.utcnow()
