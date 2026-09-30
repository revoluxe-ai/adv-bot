"""
Tests for improved token status display functionality.

Tests the new simplified token status messages and expiration date features.
"""

import datetime

from app.modules.token_monitoring.services.token_info_service import (
    TokenStatusReport,
    TokenInfo,
    REQUIRED_RIGHTS,
)


class TestImprovedTokenStatus:
    """Test cases for improved token status display."""

    def test_service_expiration_date_complete_status(self):
        """Test service expiration date calculation when status is Complete."""
        # Create token infos with different expiration dates
        token1 = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30),
            categories={"Контент", "Статистика"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        token2 = TokenInfo(
            id=2,
            api_key="key2",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=10),  # Earlier expiration
            categories={"Аналитика", "Продвижение"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token1, token2],
            valid_tokens=[token1, token2],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика", "Аналитика", "Продвижение"},
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        # Service breaks when token2 expires because unique rights are split across tokens.
        expiration_date = report.service_expiration_date
        assert expiration_date is not None
        assert expiration_date == token2.expires
        assert report.rights_lost_at_service_expiration == {
            "Аналитика",
            "Продвижение",
        }

        days_until_break = report.days_until_service_breaks
        assert days_until_break is not None
        assert 9 <= days_until_break <= 10  # Allow for timing differences

    def test_service_expiration_date_insufficient_status(self):
        """Test service expiration date when status is Insufficient (already broken)."""
        token1 = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30),
            categories={"Контент", "Статистика"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Insufficient",  # Missing required permissions
            all_tokens=[token1],
            valid_tokens=[token1],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика"},
            missing_permissions={"Аналитика", "Продвижение"},
            has_all_required_permissions=False,
            expiring_tokens=[],
        )

        # Service is already broken, so no expiration date
        assert report.service_expiration_date is None
        assert report.days_until_service_breaks is None
        assert report.rights_lost_at_service_expiration == set()

    def test_coverage_loss_is_computed_once(self):
        """Date, days-left, and lost rights share one coverage walk."""
        token = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10),
            categories=REQUIRED_RIGHTS,
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )
        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token],
            valid_tokens=[token],
            expired_tokens=[],
            available_permissions=REQUIRED_RIGHTS,
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )
        calls = 0
        original = TokenStatusReport._first_required_rights_coverage_loss.func

        def counting(
            self: TokenStatusReport,
        ) -> tuple[datetime.datetime, set[str]] | None:
            nonlocal calls
            calls += 1
            return original(self)

        TokenStatusReport._first_required_rights_coverage_loss.func = counting
        try:
            expiration_date = report.service_expiration_date
            days_until_break = report.days_until_service_breaks
            lost_rights = report.rights_lost_at_service_expiration
        finally:
            TokenStatusReport._first_required_rights_coverage_loss.func = original

        assert calls == 1
        assert expiration_date == token.expires
        assert days_until_break is not None
        assert lost_rights == REQUIRED_RIGHTS

    def test_service_expiration_only_relevant_tokens(self):
        """Test that only tokens with required permissions affect expiration date."""
        # Personal token with all required permissions.
        required_token = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=5),
            categories=REQUIRED_RIGHTS,
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        # Non-personal token with earlier expiry (ignored for service date)
        irrelevant_token = TokenInfo(
            id=2,
            api_key="key2",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(days=1),  # Earlier but irrelevant
            categories={"Цены и скидки", "Маркетплейс"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=False,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[required_token, irrelevant_token],
            valid_tokens=[required_token, irrelevant_token],
            expired_tokens=[],
            available_permissions={
                "Контент",
                "Статистика",
                "Аналитика",
                "Продвижение",
                "Цены и скидки",
                "Маркетплейс",
            },
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        # Should use required_token (5 days), not irrelevant_token (1 day)
        days_until_break = report.days_until_service_breaks
        assert days_until_break is not None
        assert 4 <= days_until_break <= 5

    def test_days_until_service_breaks_edge_cases(self):
        """Test edge cases for days calculation."""
        # Token expiring very soon
        soon_token = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(hours=12),  # Less than 1 day
            categories=REQUIRED_RIGHTS,
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[soon_token],
            valid_tokens=[soon_token],
            expired_tokens=[],
            available_permissions=REQUIRED_RIGHTS,
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        days_until_break = report.days_until_service_breaks
        assert days_until_break is not None
        assert days_until_break == 0  # Should return 0, not negative

    def test_no_valid_tokens_with_required_permissions(self):
        """Test when no valid tokens have required permissions."""
        # Token with non-required permissions only
        token = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30),
            categories={"Цены и скидки"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Insufficient",
            all_tokens=[token],
            valid_tokens=[token],
            expired_tokens=[],
            available_permissions={"Цены и скидки"},
            missing_permissions=REQUIRED_RIGHTS,
            has_all_required_permissions=False,
            expiring_tokens=[],
        )

        # No tokens with required permissions
        assert report.service_expiration_date is None
        assert report.days_until_service_breaks is None

    def test_required_rights_constant(self):
        """Verify REQUIRED_RIGHTS constant contains expected values."""
        expected_rights = {"Контент", "Статистика", "Аналитика", "Продвижение"}
        assert REQUIRED_RIGHTS == expected_rights

    def test_multiple_tokens_same_service_break_date(self):
        """Test when multiple tokens have the same service-break expiration."""
        same_date = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7)

        token1 = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=same_date,
            categories={"Контент", "Статистика"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        token2 = TokenInfo(
            id=2,
            api_key="key2",
            user_id=123,
            shop_id="shop1",
            expires=same_date,  # Same expiration
            categories={"Аналитика", "Продвижение"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token1, token2],
            valid_tokens=[token1, token2],
            expired_tokens=[],
            available_permissions=REQUIRED_RIGHTS,
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        assert report.service_expiration_date == same_date
        assert report.rights_lost_at_service_expiration == REQUIRED_RIGHTS
        days_until_break = report.days_until_service_breaks
        assert days_until_break is not None
        assert 6 <= days_until_break <= 7

    def test_service_expiration_with_redundant_rights_uses_later_date(self):
        """Service should continue if other personal tokens still cover all rights."""
        full_rights_long = TokenInfo(
            id=1,
            api_key="key1",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30),
            categories=REQUIRED_RIGHTS,
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )
        partial_short = TokenInfo(
            id=2,
            api_key="key2",
            user_id=123,
            shop_id="shop1",
            expires=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=10),
            categories={"Контент", "Статистика"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )

        report = TokenStatusReport(
            shop_id="shop1",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[full_rights_long, partial_short],
            valid_tokens=[full_rights_long, partial_short],
            expired_tokens=[],
            available_permissions=REQUIRED_RIGHTS,
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        assert report.service_expiration_date == full_rights_long.expires
        assert report.rights_lost_at_service_expiration == REQUIRED_RIGHTS
        days_until_break = report.days_until_service_breaks
        assert days_until_break is not None
        assert 29 <= days_until_break <= 30
