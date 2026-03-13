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
    }

    def __init__(self, http_session: ClientSession | None = None):
        """Initialize validator.

        Args:
            http_session: Optional aiohttp session. If None, temporary session will be created.
        """
        self._session = http_session
        self._own_session = False

    async def validate(
        self,
        api_key: str,
        *,
        mode: Literal["claims_only", "claims_plus_api"] = "claims_plus_api",
    ) -> ValidationResult:
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
                    is_read_only=False,
                    is_expired=False,
                    expires=None,
                    permissions={},
                )
            
            # Now safely access properties
            shop_id = wb_token.get_shop_id_from_token()
            is_read_only = wb_token.read_only
            is_expired = wb_token.is_expired
            expires = wb_token.expires
            jwt_categories = wb_token.categories
        except Exception as e:
            logger.warning("JWT decode failed: %s", e, exc_info=True)
            return ValidationResult(
                is_valid_jwt=False,
                shop_id=None,
                is_read_only=False,
                is_expired=False,
                expires=None,
                permissions={},
            )

        permissions = {}

        permissions["Статистика"] = PermissionStatus(
            name="Статистика",
            has_jwt_claim="Статистика" in jwt_categories,
            api_probe_success=None,
        )

        for right_name in ["Контент", "Аналитика", "Продвижение"]:
            has_claim = right_name in jwt_categories
            api_success = None

            if mode == "claims_plus_api" and has_claim:
                api_success = await self._probe_api(right_name, api_key)

            permissions[right_name] = PermissionStatus(
                name=right_name,
                has_jwt_claim=has_claim,
                api_probe_success=api_success,
            )

        return ValidationResult(
            is_valid_jwt=True,
            shop_id=shop_id,
            is_read_only=is_read_only,
            is_expired=is_expired,
            expires=expires,
            permissions=permissions,
        )

    async def _probe_api(self, right_name: str, api_key: str) -> bool:
        """Probe API endpoint to verify permission.

        Args:
            right_name: Name of the right to probe
            api_key: WB API token

        Returns:
            True if API probe successful, False otherwise
        """
        url = self.PROBE_ENDPOINTS.get(right_name)
        if not url:
            return True

        session = self._session
        close_after = False
        if session is None:
            session = ClientSession()
            close_after = True

        try:
            headers = {"Authorization": api_key}
            timeout = ClientTimeout(total=5)
            async with session.get(url, headers=headers, timeout=timeout) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("Status") == "OK"
                return False
        except Exception as e:
            logger.warning("API probe failed for %s: %s", right_name, e)
            return False
        finally:
            if close_after:
                await session.close()
