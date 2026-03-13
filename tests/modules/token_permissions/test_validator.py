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


# Valid token with all required permissions (from test_token_validation.py)
VALID_TOKEN = (
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
        assert result.can_be_used
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
        assert result.can_be_used
        assert result.error_message is None
        assert len(result.missing_required) == 0

        # Check that API probes were successful for all except Statistics
        assert result.permissions["Контент"].api_probe_success is True
        assert result.permissions["Аналитика"].api_probe_success is True
        assert result.permissions["Продвижение"].api_probe_success is True
        # Statistics should not have API probe
        assert result.permissions["Статистика"].api_probe_success is None

    @pytest.mark.asyncio
    async def test_valid_token_claims_plus_api_mode_failure(self):
        """Test validation with claims_plus_api mode when API probes fail."""
        validator = TokenPermissionsValidator()

        # Mock failed API responses
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=False)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.is_valid_jwt
        assert not result.is_read_only
        assert not result.is_expired

        # Token should NOT be usable because API probes failed
        assert not result.can_be_used
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
    async def test_invalid_token(self):
        """Test validation with invalid JWT token."""
        validator = TokenPermissionsValidator()
        result = await validator.validate(INVALID_TOKEN, mode="claims_only")

        assert not result.is_valid_jwt
        assert result.shop_id is None
        assert not result.can_be_used
        assert result.error_message == "Токен не валиден"
        assert result.permissions == {}
        assert result.is_read_only is False
        assert result.is_expired is False

    @pytest.mark.asyncio
    async def test_read_only_token(self):
        """Test validation with read-only token."""
        validator = TokenPermissionsValidator()

        # Mock WBToken to return read_only = True
        with patch("app.modules.token_permissions.validator.WBToken") as mock_token_class:
            mock_token = MagicMock()
            mock_token.check_valid.return_value = True
            mock_token.get_shop_id_from_token.return_value = "test_shop_id"
            mock_token.read_only = True
            mock_token.is_expired = False
            mock_token.expires = None
            mock_token.categories = {"Контент", "Статистика", "Аналитика", "Продвижение"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert result.is_read_only
        assert not result.can_be_used
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
            mock_token.read_only = False
            mock_token.is_expired = True
            mock_token.expires = None
            mock_token.categories = {"Контент", "Статистика", "Аналитика", "Продвижение"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert result.is_expired
        assert not result.can_be_used
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
            mock_token.read_only = False
            mock_token.is_expired = False
            mock_token.expires = None
            # Missing "Продвижение"
            mock_token.categories = {"Контент", "Статистика", "Аналитика"}
            mock_token_class.return_value = mock_token

            result = await validator.validate("test_token", mode="claims_only")

        assert result.is_valid_jwt
        assert not result.can_be_used
        assert "Продвижение" in result.missing_required
        assert "Продвижение" in result.error_message

    @pytest.mark.asyncio
    async def test_probe_api_success(self):
        """Test _probe_api method with successful response."""
        validator = TokenPermissionsValidator()

        # Mock aiohttp session
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"Status": "OK"})

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        mock_session.close = AsyncMock()

        with patch("app.modules.token_permissions.validator.ClientSession", return_value=mock_session):
            result = await validator._probe_api("Контент", "test_token")

        assert result is True

    @pytest.mark.asyncio
    async def test_probe_api_failure_non_200(self):
        """Test _probe_api method with non-200 status."""
        validator = TokenPermissionsValidator()

        # Mock aiohttp session with 403 status
        mock_response = MagicMock()
        mock_response.status = 403

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        mock_session.close = AsyncMock()

        with patch("app.modules.token_permissions.validator.ClientSession", return_value=mock_session):
            result = await validator._probe_api("Контент", "test_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_probe_api_failure_wrong_status(self):
        """Test _probe_api method with 200 but wrong Status field."""
        validator = TokenPermissionsValidator()

        # Mock aiohttp session with wrong Status
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"Status": "ERROR"})

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)
        mock_session.close = AsyncMock()

        with patch("app.modules.token_permissions.validator.ClientSession", return_value=mock_session):
            result = await validator._probe_api("Контент", "test_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_probe_api_exception(self):
        """Test _probe_api method with exception."""
        validator = TokenPermissionsValidator()

        # Mock aiohttp session to raise exception
        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Network error")
        mock_session.close = AsyncMock()

        with patch("app.modules.token_permissions.validator.ClientSession", return_value=mock_session):
            result = await validator._probe_api("Контент", "test_token")

        assert result is False

    @pytest.mark.asyncio
    async def test_validator_with_provided_session(self):
        """Test validator with externally provided session."""
        mock_session = AsyncMock(spec=ClientSession)
        validator = TokenPermissionsValidator(http_session=mock_session)

        # Mock successful API probe
        with patch.object(validator, "_probe_api", new=AsyncMock(return_value=True)):
            result = await validator.validate(VALID_TOKEN, mode="claims_plus_api")

        assert result.can_be_used

    def test_permission_status_is_available_with_api_probe(self):
        """Test PermissionStatus.is_available with API probe result."""
        # Both JWT and API probe success
        perm = PermissionStatus(name="Контент", has_jwt_claim=True, api_probe_success=True)
        assert perm.is_available

        # JWT claim but API probe failed
        perm = PermissionStatus(name="Контент", has_jwt_claim=True, api_probe_success=False)
        assert not perm.is_available

        # No JWT claim
        perm = PermissionStatus(name="Контент", has_jwt_claim=False, api_probe_success=True)
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
            is_read_only=False,
            is_expired=False,
            expires=None,
            permissions=permissions,
        )

        assert result.can_be_used
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
            is_read_only=False,
            is_expired=False,
            expires=None,
            permissions=permissions,
        )

        assert not result.can_be_used
        assert "Аналитика" in result.missing_required
        assert "Продвижение" in result.missing_required
        assert "Аналитика" in result.error_message
        assert "Продвижение" in result.error_message
