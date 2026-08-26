"""Token permissions validator for WB API."""

import logging
from typing import Literal
from aiohttp import ClientSession, ClientTimeout

from app.modules.common_slaves.wildberries.models import WBToken
from .dto import ValidationResult, PermissionStatus

logger = logging.getLogger(__name__)


class TokenPermissionsValidator:
    """Centralized validator for WB API token permissions."""

    REQUIRED_RIGHTS = {"Контент", "Статистика", "Аналитика", "Продвижение"}

    PROBE_ENDPOINTS = {
        "Контент": "https://content-api.wildberries.ru/ping",
        "Аналитика": "https://seller-analytics-api.wildberries.ru/ping",
        "Продвижение": "https://advert-api.wildberries.ru/ping",
        "Статистика": "https://statistics-api.wildberries.ru/ping"
    }

    def __init__(self, http_session: ClientSession | None = None):
        """Initialize validator.

        Args:
            http_session: Optional aiohttp session. If None, temporary session will be created.
        """
        self._session = http_session

    async def validate(
        self,
        api_key: str,
        *,
        mode: Literal["claims_only", "claims_plus_api"] = "claims_plus_api",
    ) -> ValidationResult | None:
        """Validate token and its permissions.

        Args:
            api_key: WB API token (JWT)
            mode:
                - claims_only: Only JWT validation, no API calls
                - claims_plus_api: JWT + API probe for Content/Analytics/Promotion

        Returns:
            ValidationResult with complete token and permissions information
        """
        try:
            wb_token = WBToken(api_key=api_key)
            # First check_valid to see if JWT can be decoded
            is_valid = wb_token.check_valid()
            if not is_valid:
                return ValidationResult(
                    is_valid_jwt=False,
                    shop_id=None,
                    is_personal=False,
                    is_read_only=False,
                    is_expired=False,
                    expires=None,
                    permissions={},
                )

            # Now safely access properties
            shop_id = wb_token.get_shop_id_from_token()
            is_personal = wb_token.is_personal
            is_read_only = wb_token.read_only
            is_expired = wb_token.is_expired
            expires = wb_token.expires
            jwt_categories = wb_token.categories
        except Exception as e:
            logger.warning("JWT decode failed: %s", e, exc_info=True)
            return ValidationResult(
                is_valid_jwt=False,
                shop_id=None,
                is_personal=False,
                is_read_only=False,
                is_expired=False,
                expires=None,
                permissions={},
            )

        permissions: dict[str, PermissionStatus] = {}

        permissions["Статистика"] = PermissionStatus(
            name="Статистика",
            has_jwt_claim="Статистика" in jwt_categories,
            api_probe_success=None,
        )

        # Create temporary session if needed (reused across all probes)
        temp_session = None
        if mode == "claims_plus_api" and self._session is None:
            temp_session = ClientSession()

        try:
            for right_name in ["Контент", "Аналитика", "Продвижение", "Статистика"]:
                has_claim = right_name in jwt_categories
                api_success = None

                if mode == "claims_plus_api" and has_claim:
                    api_success = await self._probe_api(right_name, api_key, temp_session)

                permissions[right_name] = PermissionStatus(
                    name=right_name,
                    has_jwt_claim=has_claim,
                    api_probe_success=api_success,
                )

            return ValidationResult(
                is_valid_jwt=True,
                shop_id=shop_id,
                is_personal=is_personal,
                is_read_only=is_read_only,
                is_expired=is_expired,
                expires=expires,
                permissions=permissions,
            )
        finally:
            if temp_session is not None:
                await temp_session.close()

    async def _probe_api(
        self,
        right_name: str,
        api_key: str,
        temp_session: ClientSession | None = None,
    ) -> bool | None:
        """Probe API endpoint to verify permission.

        Args:
            right_name: Name of the right to probe
            api_key: WB API token
            temp_session: Optional temporary session provided by caller

        Returns:
            True if API probe successful (permission verified)
            False if permission denied (HTTP 403)
            None if network/transient error (timeout, DNS, connection error, etc.)
        """
        url = self.PROBE_ENDPOINTS.get(right_name)
        if not url:
            return True

        # Use provided temp_session, fallback to instance session
        session = temp_session or self._session
        if session is None:
            raise ValueError("No session available for API probe")

        try:
            headers = {"Authorization": api_key}
            timeout = ClientTimeout(total=5)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("Status") == "OK":
                        return True
                    # HTTP 200 but Status != "OK": API format change or service issue
                    # This is NOT a permission denial, so fall back to JWT
                    logger.warning(
                        "API probe for %s returned 200 but Status=%s (not OK), treating as transient",
                        right_name,
                        data.get("Status"),
                    )
                    return None
                # HTTP 403 = permission denied (token lacks this permission)
                if resp.status == 403:
                    return False
                # Other HTTP errors (4xx, 5xx) = service issue, can't verify
                logger.warning(
                    "API probe for %s returned status %s (not 403), treating as transient",
                    right_name,
                    resp.status,
                )
                return None
        except Exception as e:
            # Network errors (timeout, DNS failure, connection refused, etc.)
            # These are transient and don't mean the token lacks permissions
            logger.warning(
                "API probe failed for %s with network/transient error: %s",
                right_name,
                e,
            )
            return None
