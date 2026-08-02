"""Tests for TokenPermissionsValidator module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aiohttp import ClientSession

from app.modules.token_permissions import (
    TokenPermissionsValidator,
    ValidationResult,
    PermissionStatus,
)

pytestmark = pytest.mark.unit


# Valid PERSONAL token with all required permissions
VALID_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpZCI6InRlc3QiLCJzIjoxMDIsInNpZCI6InRlc3Rfc2hvcCIsImV4cCI6MjAxMTgzMDMyMCwiYWNjIjozLCJmb3IiOiJzZWxmIiwidCI6ZmFsc2V9."
    "9_r9EMOX3TtN26rgezFbtP60BRrYgybaPPv7Hi4dIMc"
)

# Valid BASE token (non-personal)
NON_PERSONAL_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpZCI6IjkwODNmNDU2LWJiZGEtNDczOS1hMGYxLTMwMzRiZDhjMDczNCIsInMiOjEwMiwic2lkIjoiOTRhM2YwY2QtOGFjMS00Mjk2LTliNmUtYmE4NmNiNTQ2NGNiIiwiZXhwIjoyMDExODMwMzIwLCJhY2MiOjEsInQiOmZhbHNlfQ."
    "QeUqgoxsjJEWrJpdsFxLOsqa15EBfGkNZwf690qlUko"
)

# Invalid JWT token
INVALID_TOKEN = "invalid.jwt.token"

# Read-only token (bit 30 set)
# This token has read_only flag set (t:true in payload means read-only)
READ_ONLY_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpZCI6InRlc3QiLCJzIjoxMDIsInNpZCI6InRlc3QiLCJleHAiOjIwMTE4MzAzMjAsImFjYyI6MSwidCI6dHJ1ZX0."
    "test"
)


class TestTokenPermissionsValidator:
    """Test suite for TokenPermissionsValidator."""

    @pytest.mark.asyncio
    async def test_valid_token_claims_only_mode(self):
        """Test validation with claims_only mode for valid token."""
        validator = TokenPermissionsValidator()
        result = await validator.validate(VALID_TOKEN, mode="claims_only")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired
        assert result.shop_id is not None
        assert result.can_be_used_for_free
        assert result.can_be_used_for_pay
        assert result.error_message is None
        assert len(result.missing_required) == 0

        # Check that all required permissions are present in JWT
        for right in ["Контент", "Статистика", "Аналитика", "Продвижение"]:
            assert right in result.permissions
            assert result.permissions[right].has_jwt_claim
            # In claims_only mode, api_probe_success should be None
            assert result.permissions[right].api_probe_success is None

    @pytest.mark.asyncio
    async def test_valid_token_claims_plus_api_mode_success(self):
        """Test validation with claims_plus_api mode when API probes succeed."""
        validator = TokenPermissionsValidator()

        # Mock successful API responses
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=True)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired
        assert result.can_be_used_for_free
        assert result.can_be_used_for_pay
        assert result.error_message is None
        assert len(result.missing_required) == 0

        # claims_plus_api probes all required rights, including Статистика
        assert result.permissions["Контент"].api_probe_success is True
        assert result.permissions["Аналитика"].api_probe_success is True
        assert result.permissions["Продвижение"].api_probe_success is True

        # Statistics is now probed in claims_plus_api mode
        assert result.permissions["Статистика"].api_probe_success is True

    @pytest.mark.asyncio
    async def test_valid_token_claims_plus_api_mode_failure(self):
        """Test validation when API probes fail with 403 (permission denied)."""
        validator = TokenPermissionsValidator()

        # Mock failed API responses (403 = permission denied)
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=False)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired

        # Token should NOT be usable because API probes returned False (403)
        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert result.error_message is not None
        assert len(result.missing_required) > 0

        # Check that API probes failed
        assert result.permissions["Контент"].api_probe_success is False
        assert result.permissions["Аналитика"].api_probe_success is False
        assert result.permissions["Продвижение"].api_probe_success is False
        assert not result.permissions["Контент"].is_available
        assert not result.permissions["Аналитика"].is_available
        assert not result.permissions["Продвижение"].is_available

    @pytest.mark.asyncio
    async def test_valid_token_network_errors_fallback_to_jwt(self):
        """Test validation when API probes have network errors (should fall back to JWT claims)."""
        validator = TokenPermissionsValidator()

        # Mock network errors (returns None)
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=None)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired

        # Token SHOULD be usable - network errors don't invalidate JWT claims
        assert result.can_be_used_for_free
        assert result.can_be_used_for_pay
        assert result.error_message is None
        assert len(result.missing_required) == 0

        # Check that API probes returned None (network error)
        assert result.permissions["Контент"].api_probe_success is None
        assert result.permissions["Аналитика"].api_probe_success is None
        assert result.permissions["Продвижение"].api_probe_success is None
        # But permissions are still available based on JWT claims
        assert result.permissions["Контент"].is_available
        assert result.permissions["Аналитика"].is_available
        assert result.permissions["Продвижение"].is_available

    @pytest.mark.asyncio
    async def test_valid_token_api_format_change_fallback_to_jwt(self):
        """Test validation when API returns 200 but Status != "OK" (API format change).
        
        This scenario represents an API format change or service issue (not permission denial).
        The token should remain valid and fall back to JWT claims for validation.
        """
        validator = TokenPermissionsValidator()

        # Create a custom mock that simulates API returning 200 with Status != "OK"
        async def mock_probe_with_wrong_status(right_name, api_key, temp_session=None):
            # Simulate the actual _probe_api logic for 200 with wrong Status
            if right_name in ["Контент", "Аналитика", "Продвижение"]:
                return None  # API format issue, should return None
            return True

        with patch.object(validator, "_probe_api", side_effect=mock_probe_with_wrong_status):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired

        # Token SHOULD be usable - API format changes don't invalidate JWT claims
        assert result.can_be_used_for_free
        assert result.can_be_used_for_pay
        assert result.error_message is None
        assert len(result.missing_required) == 0

        # Permissions should be available based on JWT claims (fallback)
        assert result.permissions["Контент"].is_available
        assert result.permissions["Аналитика"].is_available
        assert result.permissions["Продвижение"].is_available

    @pytest.mark.asyncio
    async def test_invalid_token(self):
        """Test validation with invalid JWT token."""
        validator = TokenPermissionsValidator()
        result = await validator.validate(INVALID_TOKEN, mode="claims_only")

        assert not result.is_valid_jwt
        assert result.shop_id is None
        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert result.error_message == "Токен не валиден"
        assert result.permissions == {}
        assert result.is_read_only is False
        assert result.is_expired is False

    @pytest.mark.asyncio
    async def test_non_personal_token(self):
        """Test validation with non-personal token."""
        validator = TokenPermissionsValidator()
        result = await validator.validate(NON_PERSONAL_TOKEN, mode="claims_only")

        assert result.is_valid_jwt
        assert not result.is_personal
        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert result.error_message == "Токен не персональный"

    @pytest.mark.asyncio
    async def test_read_only_token(self):
        """Read-only token remains usable for analytics registration path.

        ``can_be_used`` no longer hard-fails on read-only (start UX warns after add).
        ``error_message`` still surfaces the read-only notice for callers that check it.
        """
        validator = TokenPermissionsValidator()

        # Mock WBToken to return read_only = True
        with patch("app.modules.token_permissions.validator.WBToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.check_valid.return_value = True
            mock_token.get_shop_id_from_token.return_value = "test_shop_id"
            mock_token.is_personal = True
            mock_token.read_only = True
            mock_token.is_expired = False
            mock_token.expires = None
            mock_token.categories = {"Контент", "Статистика", "Аналитика", "Продвижение"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert result.is_read_only
        assert result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert result.error_message == "Токен только для чтения"

    @pytest.mark.asyncio
    async def test_expired_token(self):
        """Test validation with expired token."""
        validator = TokenPermissionsValidator()

        # Mock WBToken to return is_expired = True
        with patch("app.modules.token_permissions.validator.WBToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.check_valid.return_value = True
            mock_token.get_shop_id_from_token.return_value = "test_shop_id"
            mock_token.is_personal = True
            mock_token.read_only = False
            mock_token.is_expired = True
            mock_token.expires = None
            mock_token.categories = {"Контент", "Статистика", "Аналитика", "Продвижение"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert result.is_expired
        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert result.error_message == "Токен истёк"

    @pytest.mark.asyncio
    async def test_missing_permissions(self):
        """Test validation with token missing required permissions."""
        validator = TokenPermissionsValidator()

        # Mock WBToken with only some permissions
        with patch("app.modules.token_permissions.validator.WBToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.check_valid.return_value = True
            mock_token.get_shop_id_from_token.return_value = "test_shop_id"
            mock_token.is_personal = True
            mock_token.read_only = False
            mock_token.is_expired = False
            mock_token.expires = None
            # Missing "Продвижение"
            mock_token.categories = {"Контент", "Статистика", "Аналитика"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert "Продвижение" in result.missing_required
        assert "Продвижение" in result.error_message

    @pytest.mark.asyncio
    async def test_probe_api_success(self):
        """Test _probe_api method with successful response."""
        # Mock aiohttp session
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"Status": "OK"})

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        assert result is True

    @pytest.mark.asyncio
    async def test_probe_api_failure_non_200(self):
        """Test _probe_api method with 403 status (permission denied)."""
        # Mock aiohttp session with 403 status
        mock_response = MagicMock()
        mock_response.status = 403

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        # 403 = permission denied, definitive False
        assert result is False

    @pytest.mark.asyncio
    async def test_probe_api_500_error(self):
        """Test _probe_api with 500 status (server error, transient)."""
        mock_response = MagicMock()
        mock_response.status = 500

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        # 5xx = service issue, can't verify → None
        assert result is None

    @pytest.mark.asyncio
    async def test_probe_api_404_error(self):
        """Test _probe_api with 404 status (not found, transient issue)."""
        mock_response = MagicMock()
        mock_response.status = 404

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        # 404 (not 403) = service issue, can't verify → None
        assert result is None

    @pytest.mark.asyncio
    async def test_probe_api_failure_wrong_status(self):
        """Test _probe_api method with 200 but wrong Status field.
        
        HTTP 200 with Status != "OK" is treated as a transient/service issue,
        not a permission denial. This allows fallback to JWT validation.
        """
        # Mock aiohttp session with wrong Status
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"Status": "ERROR"})

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        # Should return None (transient error), not False (permission denied)
        assert result is None

    @pytest.mark.asyncio
    async def test_probe_api_exception(self):
        """Test _probe_api method with exception (network error)."""
        # Mock aiohttp session to raise exception
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")

        validator = TokenPermissionsValidator()
        result = await validator._probe_api("Контент", "test_token", mock_session)

        # Network errors should return None (can't verify, not a definitive failure)
        assert result is None

    @pytest.mark.asyncio
    async def test_validator_with_provided_session(self):
        """Test validator with externally provided session."""
        mock_session = AsyncMock(spec=ClientSession)
        validator = TokenPermissionsValidator(http_session=mock_session)

        # Mock successful API probe
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=True)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.can_be_used_for_pay

    @pytest.mark.asyncio
    async def test_session_reuse_across_multiple_probes(self):
        """Test that a single temporary session is reused across multiple API probes."""
        validator = TokenPermissionsValidator()

        # Mock ClientSession creation
        mock_session = MagicMock()
        mock_session.close = AsyncMock()

        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"Status": "OK"})

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session.get = MagicMock(return_value=mock_get_cm)

        with patch("app.modules.token_permissions.validator.ClientSession", return_value=mock_session) as mock_session_class:
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        # Verify session was created only once despite 4 API probes
        assert mock_session_class.call_count == 1
        # Verify session was closed exactly once
        assert mock_session.close.call_count == 1
        # Verify all required probes succeeded (including Статистика)
        assert result.permissions["Контент"].api_probe_success is True
        assert result.permissions["Аналитика"].api_probe_success is True
        assert result.permissions["Продвижение"].api_probe_success is True
        assert result.permissions["Статистика"].api_probe_success is True

    def test_permission_status_is_available_with_api_probe(self):
        """Test PermissionStatus.is_available with API probe result."""
        # Both JWT and API probe success
        perm = PermissionStatus(name="Контент", has_jwt_claim=True, api_probe_success=True)
        assert perm.is_available

        # JWT claim but API probe failed (403 = permission denied)
        perm = PermissionStatus(name="Контент", has_jwt_claim=True, api_probe_success=False)
        assert not perm.is_available

        # No JWT claim, even if API probe succeeded (shouldn't happen in practice)
        perm = PermissionStatus(name="Контент", has_jwt_claim=False, api_probe_success=True)
        assert not perm.is_available

    def test_permission_status_is_available_with_network_error(self):
        """Test PermissionStatus.is_available when API probe has network error (None)."""
        # JWT claim + network error (None) → fall back to JWT, available
        perm = PermissionStatus(name="Контент", has_jwt_claim=True, api_probe_success=None)
        assert perm.is_available

        # No JWT claim + network error → still unavailable
        perm = PermissionStatus(name="Контент", has_jwt_claim=False, api_probe_success=None)
        assert not perm.is_available

    def test_permission_status_is_available_without_api_probe(self):
        """Test PermissionStatus.is_available without API probe (None)."""
        # JWT claim only (Statistics case)
        perm = PermissionStatus(name="Статистика", has_jwt_claim=True, api_probe_success=None)
        assert perm.is_available

        # No JWT claim
        perm = PermissionStatus(name="Статистика", has_jwt_claim=False, api_probe_success=None)
        assert not perm.is_available

    def test_validation_result_properties(self):
        """Test ValidationResult computed properties."""
        permissions = {
            "Контент": PermissionStatus("Контент", True, True),
            "Аналитика": PermissionStatus("Аналитика", True, True),
            "Статистика": PermissionStatus("Статистика", True, None),
            "Продвижение": PermissionStatus("Продвижение", True, True),
        }

        result = ValidationResult(
            is_valid_jwt=True,
            shop_id="test_shop",
            is_personal=True,
            is_read_only=False,
            is_expired=False,
            expires=None,
            permissions=permissions,
        )

        assert result.can_be_used_for_free
        assert result.can_be_used_for_pay
        assert len(result.missing_required) == 0
        assert result.error_message is None

    def test_validation_result_missing_required(self):
        """Test ValidationResult with missing required permissions."""
        permissions = {
            "Контент": PermissionStatus("Контент", True, True),
            "Аналитика": PermissionStatus("Аналитика", False, None),  # Missing
            "Статистика": PermissionStatus("Статистика", True, None),
            "Продвижение": PermissionStatus("Продвижение", True, False),  # API probe failed
        }

        result = ValidationResult(
            is_valid_jwt=True,
            shop_id="test_shop",
            is_personal=True,
            is_read_only=False,
            is_expired=False,
            expires=None,
            permissions=permissions,
        )

        assert not result.can_be_used_for_free
        assert not result.can_be_used_for_pay
        assert "Аналитика" in result.missing_required
        assert "Продвижение" in result.missing_required
        assert "Аналитика" in result.error_message
        assert "Продвижение" in result.error_message
