"""Token information service for analyzing token permissions and validity."""

import datetime
import logging
from dataclasses import dataclass
from functools import cached_property

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.common_slaves.wildberries.models import (
    WBToken,
    WBUserCabinet,
)
from app.modules.common_slaves.wildberries.models.wb_cabinet import WBCabinet
from app.utils.db.session_maker import get_async_session_maker

logger = logging.getLogger(__name__)

# Required rights for the bot to function properly
REQUIRED_RIGHTS = {
    "Контент",  # Content
    "Статистика",  # Statistics
    "Аналитика",  # Analytics
    "Продвижение",  # Promotion
}


# TODO: Подписать РК где Авто, где Аукцион

# --- Time helpers (ensure timezone-aware UTC) ---


def utcnow() -> datetime.datetime:
    """Return current time as timezone-aware UTC datetime."""
    return datetime.datetime.now(datetime.UTC)


def _to_aware_utc(dt: datetime.datetime) -> datetime.datetime:
    """Convert any datetime to timezone-aware UTC.

    Assumptions:
    - If datetime is naive (no tzinfo), it's treated as UTC.
    - If datetime is tz-aware, it's converted to UTC.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=datetime.UTC)
    return dt.astimezone(datetime.UTC)


@dataclass
class TokenInfo:
    """Information about a single token."""

    id: int
    api_key: str
    user_id: int
    shop_id: str
    expires: datetime.datetime
    categories: set[str]
    is_read_only: bool
    is_valid: bool
    is_expired: bool
    is_personal: bool

    @classmethod
    def from_wb_token(cls, wb_token: WBToken) -> "TokenInfo":
        """Create TokenInfo from WBToken model."""
        now = utcnow()
        expires_utc = _to_aware_utc(wb_token.expires)
        return cls(
            id=wb_token.id,
            api_key=wb_token.api_key,
            user_id=wb_token.user_id,
            shop_id=wb_token.shop_id or "",
            expires=expires_utc,
            categories=wb_token.categories,
            is_read_only=wb_token.read_only,
            is_valid=wb_token.check_valid(),
            is_expired=expires_utc <= now,
            is_personal=wb_token.is_personal,
        )


@dataclass
class ExpiringToken:
    """Information about a token that is expiring soon."""

    token_info: TokenInfo
    days_until_expiry: int
    shop_name: str

    @property
    def expiry_date_str(self) -> str:
        """Get formatted expiry date string."""
        return self.token_info.expires.strftime("%d.%m.%Y")


@dataclass
class PermissionValidation:
    """Result of permission validation for specific functionality."""

    has_access: bool
    missing_permissions: set[str]
    available_permissions: set[str]
    error_message: str | None = None


@dataclass
class TokenStatusReport:
    """Comprehensive token status report for a shop."""

    shop_id: str
    shop_name: str
    status: str  # "Complete" or "Insufficient"
    all_tokens: list[TokenInfo]
    valid_tokens: list[TokenInfo]
    expired_tokens: list[TokenInfo]
    available_permissions: set[str]
    missing_permissions: set[str]
    has_all_required_permissions: bool
    expiring_tokens: list[ExpiringToken]

    @property
    def total_tokens(self) -> int:
        """Total number of tokens for this shop."""
        return len(self.all_tokens)

    @property
    def valid_token_count(self) -> int:
        """Number of valid (non-expired, non-read-only) tokens."""
        return len(self.valid_tokens)

    @property
    def has_valid_tokens(self) -> bool:
        """Check if shop has any valid tokens."""
        return self.valid_token_count > 0

    @property
    def status_description(self) -> str:
        """Human-readable status description."""
        if self.status == "Complete":
            return f"Все необходимые права доступны через {self.valid_token_count} токен(ов)"
        else:
            missing = ", ".join(sorted(self.missing_permissions))
            return f"Отсутствуют права: {missing}"

    @cached_property
    def _first_required_rights_coverage_loss(
        self,
    ) -> tuple[datetime.datetime, set[str]] | None:
        """First expiry moment when required-rights coverage drops to zero.

        Walks personal valid tokens grouped by exact ``expires`` datetime (ascending).
        For each group, decrements coverage for all tokens in the group before
        checking for lost rights. The result is cached for the lifetime of this
        report so date, days-left, and lost-rights reads share one pass.

        Returns:
            ``(expires, lost_rights)`` at the first coverage loss, or ``None`` if
            status is not Complete, no contributing personal tokens, or no loss.
        """
        if self.status != "Complete":
            return None

        personal_tokens = [
            token
            for token in self.valid_tokens
            if token.is_personal and (token.categories & REQUIRED_RIGHTS)
        ]
        if not personal_tokens:
            return None

        rights_coverage_count: dict[str, int] = {right: 0 for right in REQUIRED_RIGHTS}
        for token in personal_tokens:
            for right in token.categories & REQUIRED_RIGHTS:
                rights_coverage_count[right] += 1

        if any(count == 0 for count in rights_coverage_count.values()):
            return None

        sorted_tokens = sorted(personal_tokens, key=lambda t: t.expires)
        index = 0
        while index < len(sorted_tokens):
            expires_at = sorted_tokens[index].expires
            group: list[TokenInfo] = []
            while (
                index < len(sorted_tokens)
                and sorted_tokens[index].expires == expires_at
            ):
                group.append(sorted_tokens[index])
                index += 1

            for token in group:
                for right in token.categories & REQUIRED_RIGHTS:
                    rights_coverage_count[right] -= 1

            lost = {
                right
                for right, count in rights_coverage_count.items()
                if count == 0
            }
            if lost:
                return (expires_at, lost)

        return None

    @property
    def service_expiration_date(self) -> datetime.datetime | None:
        """Date when required-rights coverage is first lost for personal tokens.

        Uses only personal valid tokens that contribute at least one required right.
        The returned date is the earliest token expiry moment after which the union
        of active personal-token rights no longer covers REQUIRED_RIGHTS.
        Delegates to ``_first_required_rights_coverage_loss``.
        """
        loss = self._first_required_rights_coverage_loss
        return loss[0] if loss else None

    @property
    def rights_lost_at_service_expiration(self) -> set[str]:
        """Required rights whose coverage hits zero at ``service_expiration_date``.

        Пустое множество, если статус не Complete или дата потери покрытия не определена.
        """
        loss = self._first_required_rights_coverage_loss
        return set(loss[1]) if loss else set()

    @property
    def days_until_service_breaks(self) -> int | None:
        """Days until first personal-token coverage loss (see service_expiration_date)."""
        expiration_date = self.service_expiration_date
        if expiration_date:
            days = (expiration_date - utcnow()).days
            return max(0, days)  # Don't return negative days
        return None


class TokenInfoService:
    """Service for analyzing token permissions and status."""

    def __init__(self, session_maker=None) -> None:
        self.session_maker = session_maker or get_async_session_maker

    async def get_shop_token_status(self, shop_id: str) -> TokenStatusReport:
        """
        Get comprehensive token status report for a shop.

        Args:
            shop_id: The shop ID to analyze

        Returns:
            TokenStatusReport with complete status analysis
        """
        async with self.session_maker() as session:
            # Get all tokens for this shop
            all_tokens = await self._get_shop_tokens(session, shop_id)

            # Get shop name
            shop_name = await self._get_shop_name(session, shop_id)

            # Analyze tokens
            token_infos = [TokenInfo.from_wb_token(token) for token in all_tokens]
            valid_tokens = [
                t
                for t in token_infos
                if t.is_valid and not t.is_expired and not t.is_read_only
            ]
            expired_tokens = [t for t in token_infos if t.is_expired]

            # Aggregate permissions from valid tokens
            available_permissions = set()
            for token in valid_tokens:
                available_permissions.update(token.categories)

            # Check for missing permissions
            missing_permissions = REQUIRED_RIGHTS - available_permissions
            has_all_required = len(missing_permissions) == 0

            # Determine status
            status = "Complete" if has_all_required and valid_tokens else "Insufficient"

            # Find expiring tokens
            expiring_tokens = await self._get_expiring_tokens(
                session, shop_id, shop_name
            )

            return TokenStatusReport(
                shop_id=shop_id,
                shop_name=shop_name,
                status=status,
                all_tokens=token_infos,
                valid_tokens=valid_tokens,
                expired_tokens=expired_tokens,
                available_permissions=available_permissions,
                missing_permissions=missing_permissions,
                has_all_required_permissions=has_all_required,
                expiring_tokens=expiring_tokens,
            )

    async def validate_permissions(
        self, shop_id: str, required_rights: set[str]
    ) -> PermissionValidation:
        """
        Validate if shop has specific permissions available.

        Args:
            shop_id: The shop ID to check
            required_rights: Set of required permission names

        Returns:
            PermissionValidation with access status and details
        """
        async with self.session_maker() as session:
            # Get valid tokens for this shop
            tokens = await self._get_shop_tokens(session, shop_id)
            token_infos = [TokenInfo.from_wb_token(token) for token in tokens]
            valid_tokens = [
                t
                for t in token_infos
                if t.is_valid and not t.is_expired and not t.is_read_only
            ]

            if not valid_tokens:
                return PermissionValidation(
                    has_access=False,
                    missing_permissions=required_rights,
                    available_permissions=set(),
                    error_message="Нет действующих токенов для магазина",
                )

            # Aggregate available permissions
            available_permissions = set()
            for token in valid_tokens:
                available_permissions.update(token.categories)

            missing_permissions = required_rights - available_permissions
            has_access = len(missing_permissions) == 0

            error_message = None
            if not has_access:
                missing_str = ", ".join(sorted(missing_permissions))
                error_message = f"Отсутствуют необходимые права: {missing_str}"

            return PermissionValidation(
                has_access=has_access,
                missing_permissions=missing_permissions,
                available_permissions=available_permissions,
                error_message=error_message,
            )

    async def get_expiring_tokens(
        self, shop_id: str, days_ahead: int = 14
    ) -> list[ExpiringToken]:
        """
        Get tokens that are expiring within specified number of days.

        Args:
            shop_id: The shop ID to check
            days_ahead: Number of days to look ahead (default: 14)

        Returns:
            List of ExpiringToken objects
        """
        async with self.session_maker() as session:
            shop_name = await self._get_shop_name(session, shop_id)
            return await self._get_expiring_tokens(
                session, shop_id, shop_name, days_ahead
            )

    @staticmethod
    async def _get_shop_tokens(
        session: AsyncSession, shop_id: str
    ) -> list[WBToken]:
        """Get all tokens for a shop."""
        stmt = select(WBToken).where(WBToken.shop_id == shop_id)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def _get_tokens_by_shop_ids(
        session: AsyncSession, shop_ids: list[str]
    ) -> dict[str, list[WBToken]]:
        """Get all tokens for multiple shops in one query. Returns dict shop_id -> tokens."""
        if not shop_ids:
            return {}
        stmt = select(WBToken).where(WBToken.shop_id.in_(shop_ids))
        result = await session.execute(stmt)
        tokens = list(result.scalars().all())
        by_shop: dict[str, list[WBToken]] = {sid: [] for sid in shop_ids}
        for t in tokens:
            if t.shop_id is not None:
                by_shop.setdefault(t.shop_id, []).append(t)
        return by_shop

    async def get_shop_ids_with_complete_token_status_batch(
        self, session: AsyncSession, shop_ids: list[str]
    ) -> set[str]:
        """
        Same logic as get_shop_token_status(shop_id).status == "Complete", but for
        many shop_ids in one session and one query. Used to speed up the shops list.
        """
        if not shop_ids:
            return set()
        by_shop = await self._get_tokens_by_shop_ids(session, shop_ids)
        out: set[str] = set()
        for sid in shop_ids:
            all_tokens = by_shop.get(sid) or []
            token_infos = [TokenInfo.from_wb_token(t) for t in all_tokens]
            valid_tokens = [
                t
                for t in token_infos
                if t.is_valid and not t.is_expired and not t.is_read_only
            ]
            available_permissions: set[str] = set()
            for t in valid_tokens:
                available_permissions.update(t.categories)
            missing = REQUIRED_RIGHTS - available_permissions
            if len(missing) == 0 and valid_tokens:
                out.add(sid)
        return out

    @staticmethod
    async def _get_shop_name(session: AsyncSession, shop_id: str) -> str:
        """Get shop name from WBUserCabinet."""
        stmt = (
            select(WBUserCabinet.name)
            .join(WBCabinet)
            .where(WBCabinet.shop_id == shop_id)
            .limit(1)
        )
        result = await session.execute(stmt)
        shop_name = result.scalar()
        return shop_name or f"Магазин {shop_id}"

    @staticmethod
    async def _get_expiring_tokens(
        session: AsyncSession,
        shop_id: str,
        shop_name: str,
        days_ahead: int = 14,
    ) -> list[ExpiringToken]:
        """Get tokens expiring within specified days."""
        cutoff_date = utcnow() + datetime.timedelta(days=days_ahead)
        now = utcnow()

        # Query all tokens for the shop (can't use .expires in WHERE clause since it's a property)
        stmt = select(WBToken).where(WBToken.shop_id == shop_id)
        result = await session.execute(stmt)
        tokens = list(result.scalars().all())

        expiring_tokens = []

        for token in tokens:
            try:
                # Check if token expires within the specified timeframe
                # We need to access the property in Python, not in SQL
                token_expires = _to_aware_utc(token.expires)

                # Filter tokens that expire within the timeframe but haven't expired yet
                if cutoff_date >= token_expires > now:
                    token_info = TokenInfo.from_wb_token(token)
                    if token_info.is_valid and not token_info.is_read_only:
                        days_until_expiry = (token_expires - now).days
                        expiring_token = ExpiringToken(
                            token_info=token_info,
                            days_until_expiry=days_until_expiry,
                            shop_name=shop_name,
                        )
                        expiring_tokens.append(expiring_token)
            except Exception as e:
                # Skip tokens with invalid JWT or other issues
                # This handles cases where token.expires property fails (invalid JWT, etc.)
                logging.warning(
                    f"Skipping token {token.id} due to error accessing expires property: {e}"
                )
                continue

        return expiring_tokens


# Convenience functions for common use cases
async def get_shop_token_status(shop_id: str) -> TokenStatusReport:
    """Get token status for a shop."""
    service = TokenInfoService()
    return await service.get_shop_token_status(shop_id)


async def get_shop_ids_with_complete_token_status(
    shop_ids: list[str],
) -> set[str]:
    """
    Return set of shop_id for which token status is Complete (same logic as shop menu:
    valid tokens, not expired, not read-only, all required permissions present).
    Uses one DB session and one query for all shop_ids to avoid N round-trips.
    """
    if not shop_ids:
        return set()
    service = TokenInfoService()
    async with service.session_maker() as session:
        return await service.get_shop_ids_with_complete_token_status_batch(
            session, shop_ids
        )


async def validate_shop_permissions(
    shop_id: str, required_rights: set[str] | None = None
) -> PermissionValidation:
    """Validate shop permissions."""
    if required_rights is None:
        required_rights = REQUIRED_RIGHTS

    service = TokenInfoService()
    return await service.validate_permissions(shop_id, required_rights)


async def get_expiring_tokens_for_shop(
    shop_id: str, days_ahead: int = 14
) -> list[ExpiringToken]:
    """Get expiring tokens for a shop."""
    service = TokenInfoService()
    return await service.get_expiring_tokens(shop_id, days_ahead)
