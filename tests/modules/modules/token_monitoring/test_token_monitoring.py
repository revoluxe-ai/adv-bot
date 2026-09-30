"""Tests for ShopMenu token monitoring integration."""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.shop_menu.message import ShopMenu
from app.modules.token_monitoring.services.token_info_service import (
    TokenInfo,
    TokenStatusReport,
)


def _shop_menu_token_text(token_status: TokenStatusReport) -> str:
    """Render ShopMenu.text with only the fields the token section needs."""
    shop_menu = MagicMock(spec=ShopMenu)
    shop_menu._balance = 1000.0
    shop_menu._bonus = 200.0
    shop_menu._total_active_advs_count = 1
    shop_menu._tariff_details = None
    shop_menu._last_charge_at = None
    shop_menu._shop_balance_snapshot = None
    shop_menu._format_cashback_snapshot_line = ShopMenu._format_cashback_snapshot_line
    shop_menu._token_status_loaded = True
    shop_menu._token_status = token_status
    shop_menu._wb_user_cabinet = MagicMock()
    shop_menu._wb_user_cabinet.name = "Test Shop"
    shop_menu._wb_cabinet = MagicMock()
    shop_menu._wb_cabinet.shop_id = "test_shop_123"
    shop_menu._wb_cabinet.active = True
    rendered = ShopMenu.text.__get__(shop_menu, ShopMenu)
    assert isinstance(rendered, str)
    return rendered


class TestShopMenuTokenIntegration:
    """Test cases for ShopMenu with token monitoring integration."""

    @pytest.fixture
    def mock_bot(self):
        """Mock Telegram bot."""
        return AsyncMock()

    @pytest.fixture
    def mock_state(self):
        """Mock FSMContext state."""
        state = AsyncMock()
        state.update_data = AsyncMock()
        return state

    @pytest.fixture
    def mock_session_maker(self):
        """Mock session maker."""
        session = AsyncMock()
        session_maker = MagicMock()
        session_maker.return_value.__aenter__.return_value = session
        session_maker.return_value.__aexit__.return_value = None
        return session_maker, session

    @pytest.fixture
    def sample_wb_user_cabinet(self):
        """Create sample WBUserCabinet with related data."""
        # Create user
        user = MagicMock()
        user.user_telegram_id = 123456789

        # Create cabinet - avoid spec to prevent SQLAlchemy hybrid property issues
        wb_cabinet = MagicMock()
        wb_cabinet.id = 1
        wb_cabinet.shop_id = "test_shop_123"
        wb_cabinet.balance = 1000.0
        wb_cabinet.bonus = 200.0
        wb_cabinet.calculated_balance = 1000.0
        wb_cabinet.calculated_bonus = 200.0
        wb_cabinet.expiration_time = datetime.datetime.now() + datetime.timedelta(
            days=30
        )
        wb_cabinet.adv_settings = []
        wb_cabinet.bonus_payments = []
        wb_cabinet.balance_payments = []

        # Create user cabinet
        wb_user_cabinet = MagicMock()
        wb_user_cabinet.id = 1
        wb_user_cabinet.name = "Test Shop"
        wb_user_cabinet.user = user
        wb_user_cabinet.wb_cabinet = wb_cabinet

        return wb_user_cabinet

    @pytest.fixture
    def sample_token_status_complete(self):
        """Create sample complete token status."""
        token_info = MagicMock()
        token_info.is_valid = True
        token_info.is_expired = False
        token_info.is_read_only = False
        token_info.is_personal = True
        token_info.categories = {
            "Контент",
            "Статистика",
            "Аналитика",
            "Продвижение",
        }
        token_info.expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)

        return TokenStatusReport(
            shop_id="test_shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token_info],
            valid_tokens=[token_info],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика", "Аналитика", "Продвижение"},
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

    @pytest.fixture
    def sample_token_status_insufficient(self):
        """Create sample insufficient token status."""
        token_info = MagicMock()
        token_info.is_valid = True
        token_info.is_expired = False
        token_info.is_read_only = False
        token_info.is_personal = True
        token_info.categories = {"Контент", "Статистика"}
        token_info.expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=30)

        return TokenStatusReport(
            shop_id="test_shop_123",
            shop_name="Test Shop",
            status="Insufficient",
            all_tokens=[token_info],
            valid_tokens=[token_info],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика"},
            missing_permissions={"Аналитика", "Продвижение"},
            has_all_required_permissions=False,
            expiring_tokens=[],
        )

    @pytest.fixture
    def sample_token_status_expiring(self):
        """Create sample token status with expiring tokens."""
        from app.modules.token_monitoring.services.token_info_service import (
            ExpiringToken,
        )

        token_info = MagicMock()
        token_info.is_valid = True
        token_info.is_expired = False
        token_info.is_read_only = False
        token_info.is_personal = True
        token_info.categories = {
            "Контент",
            "Статистика",
            "Аналитика",
            "Продвижение",
        }
        token_info.expires = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=3)

        expiring_token = ExpiringToken(
            token_info=token_info, days_until_expiry=3, shop_name="Test Shop"
        )

        return TokenStatusReport(
            shop_id="test_shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[token_info],
            valid_tokens=[token_info],
            expired_tokens=[],
            available_permissions={"Контент", "Статистика", "Аналитика", "Продвижение"},
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[expiring_token],
        )

    @pytest.mark.asyncio
    async def test_shop_menu_text_with_complete_tokens(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status_complete
    ):
        """Test ShopMenu text generation with complete token status."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            with patch(
                "app.modules.shop_menu.message.TokenInfoService"
            ) as mock_token_service_class:
                # Setup mocks
                mock_token_service_instance = AsyncMock()
                mock_token_service_instance.get_shop_token_status.return_value = (
                    sample_token_status_complete
                )
                mock_token_service_class.return_value = mock_token_service_instance

                mock_result = MagicMock()
                mock_result.scalar_one = MagicMock(return_value=sample_wb_user_cabinet)
                mock_sm.return_value.__aenter__.return_value.execute.return_value = (
                    mock_result
                )

                # Mock pricer methods - these are async methods
                with patch(
                    "app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs",
                    new_callable=AsyncMock,
                ) as mock_month_tariff:
                    with patch(
                        "app.modules.billing.pricer.Pricer.get_price_for_day_for_shop",
                        new_callable=AsyncMock,
                    ) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100

                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1,
                            redis_client=None,
                        )
                        await shop_menu._load_all_data()

                        text = shop_menu.text

                        # Verify token status information is included
                        assert "\n🔑 <b>Токены:</b> ✅ <b>Все в порядке</b>\n" in text
                        assert (
                            "Отсутствуют права" not in text
                        )  # Should not show missing permissions
                        assert (
                            "⏰ Сервис перестанет работать" in text
                        )  # Verify expiration date is shown

    @pytest.mark.asyncio
    async def test_shop_menu_text_with_insufficient_tokens(
        self,
        mock_bot,
        mock_state,
        sample_wb_user_cabinet,
        sample_token_status_insufficient,
    ):
        """Test ShopMenu text generation with insufficient token status."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            with patch(
                "app.modules.shop_menu.message.TokenInfoService"
            ) as mock_token_service_class:
                mock_token_service_instance = AsyncMock()
                mock_token_service_instance.get_shop_token_status.return_value = (
                    sample_token_status_insufficient
                )
                mock_token_service_class.return_value = mock_token_service_instance

                mock_result = MagicMock()
                mock_result.scalar_one = MagicMock(return_value=sample_wb_user_cabinet)
                mock_sm.return_value.__aenter__.return_value.execute.return_value = (
                    mock_result
                )

                with patch(
                    "app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs",
                    new_callable=AsyncMock,
                ) as mock_month_tariff:
                    with patch(
                        "app.modules.billing.pricer.Pricer.get_price_for_day_for_shop",
                        new_callable=AsyncMock,
                    ) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100

                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1,
                            redis_client=None,
                        )
                        await shop_menu._load_all_data()

                        text = shop_menu.text

                        # Verify token status information shows problems
                        assert (
                            "\n🔑 <b>Токены:</b> ❌ <b>Требуется обновление</b>\n"
                            in text
                        )
                        assert (
                            "❌ <b>Отсутствуют права:</b> Аналитика, Продвижение\n"
                            in text
                        )
                        assert (
                            "🔧 <b>Добавьте новые токены для восстановления работы</b>\n"
                            in text
                        )

    @pytest.mark.asyncio
    async def test_shop_menu_text_with_expiring_tokens(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status_expiring
    ):
        """Test ShopMenu text generation with expiring tokens."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            with patch(
                "app.modules.shop_menu.message.TokenInfoService"
            ) as mock_token_service_class:
                mock_token_service_instance = AsyncMock()
                mock_token_service_instance.get_shop_token_status.return_value = (
                    sample_token_status_expiring
                )
                mock_token_service_class.return_value = mock_token_service_instance

                mock_result = MagicMock()
                mock_result.scalar_one = MagicMock(return_value=sample_wb_user_cabinet)
                mock_sm.return_value.__aenter__.return_value.execute.return_value = (
                    mock_result
                )

                with patch(
                    "app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs",
                    new_callable=AsyncMock,
                ) as mock_month_tariff:
                    with patch(
                        "app.modules.billing.pricer.Pricer.get_price_for_day_for_shop",
                        new_callable=AsyncMock,
                    ) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100

                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1,
                            redis_client=None,
                        )
                        await shop_menu._load_all_data()

                        text = shop_menu.text

                        # Verify expiring token warning is shown
                        assert "\n🔑 <b>Токены:</b> ✅ <b>Все в порядке</b>\n" in text
                        assert "🚨 <b>Сервис перестанет работать" in text
                        assert (
                            "Истекут права: Аналитика, Контент, Продвижение, Статистика\n"
                            in text
                        )

    def test_shop_menu_text_lists_only_rights_lost_on_split_tokens(self):
        """Early token drops only its own rights; the menu line names those rights."""
        now = datetime.datetime.now(datetime.UTC)
        early = TokenInfo(
            id=1,
            api_key="key-early",
            user_id=1,
            shop_id="test_shop_123",
            expires=now + datetime.timedelta(days=10),
            categories={"Аналитика", "Продвижение"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )
        later = TokenInfo(
            id=2,
            api_key="key-later",
            user_id=1,
            shop_id="test_shop_123",
            expires=now + datetime.timedelta(days=30),
            categories={"Контент", "Статистика"},
            is_read_only=False,
            is_valid=True,
            is_expired=False,
            is_personal=True,
        )
        report = TokenStatusReport(
            shop_id="test_shop_123",
            shop_name="Test Shop",
            status="Complete",
            all_tokens=[early, later],
            valid_tokens=[early, later],
            expired_tokens=[],
            available_permissions={
                "Контент",
                "Статистика",
                "Аналитика",
                "Продвижение",
            },
            missing_permissions=set(),
            has_all_required_permissions=True,
            expiring_tokens=[],
        )

        text = _shop_menu_token_text(report)

        assert "⏰ Сервис перестанет работать" in text
        assert "Истекут права: Аналитика, Продвижение\n" in text
        assert "Истекут права: Аналитика, Контент" not in text

    @pytest.mark.asyncio
    async def test_shop_menu_text_with_token_loading_error(
        self, mock_bot, mock_state, sample_wb_user_cabinet
    ):
        """Test ShopMenu text generation when token loading fails."""
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            with patch(
                "app.modules.shop_menu.message.TokenInfoService"
            ) as mock_token_service_class:
                mock_token_service_instance = AsyncMock()
                mock_token_service_instance.get_shop_token_status.side_effect = (
                    Exception("Token service error")
                )
                mock_token_service_class.return_value = mock_token_service_instance

                mock_result = MagicMock()
                mock_result.scalar_one = MagicMock(return_value=sample_wb_user_cabinet)
                mock_sm.return_value.__aenter__.return_value.execute.return_value = (
                    mock_result
                )

                with patch(
                    "app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs",
                    new_callable=AsyncMock,
                ) as mock_month_tariff:
                    with patch(
                        "app.modules.billing.pricer.Pricer.get_price_for_day_for_shop",
                        new_callable=AsyncMock,
                    ) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100

                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1,
                            redis_client=None,
                        )
                        await shop_menu._load_all_data()

                        text = shop_menu.text

                        # Verify error message is shown
                        assert "\n🔑 <b>Токены:</b> ⚠️ <b>Ошибка загрузки</b>\n" in text

    @pytest.mark.asyncio
    async def test_token_status_actually_loaded_during_data_loading(
        self, mock_bot, mock_state, sample_wb_user_cabinet, sample_token_status_complete
    ):
        """
        CRITICAL TEST: This test would have caught the original bug.

        The existing tests manually set _token_status and _token_status_loaded,
        but this test actually calls _load_all_data() to verify token loading works.
        """
        with patch("app.modules.shop_menu.message.sm") as mock_sm:
            with patch(
                "app.modules.shop_menu.message.TokenInfoService"
            ) as mock_token_service_class:
                # Setup database mocks - properly mock the async context manager
                mock_session = AsyncMock()
                mock_context_manager = AsyncMock()
                mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
                mock_context_manager.__aexit__ = AsyncMock(return_value=None)
                mock_sm.return_value = mock_context_manager

                # Mock the database query result
                mock_result = MagicMock()  # Result object is not async
                mock_result.scalar_one = MagicMock(
                    return_value=sample_wb_user_cabinet
                )  # scalar_one() is sync
                mock_session.execute = AsyncMock(
                    return_value=mock_result
                )  # execute() is async

                # Mock token status service
                mock_token_service = AsyncMock()
                mock_token_service.get_shop_token_status = AsyncMock(
                    return_value=sample_token_status_complete
                )
                mock_token_service_class.return_value = mock_token_service

                # Mock pricer methods - these are async methods
                with patch(
                    "app.modules.billing.pricer.Pricer.get_month_tariff_for_count_advs",
                    new_callable=AsyncMock,
                ) as mock_month_tariff:
                    with patch(
                        "app.modules.billing.pricer.Pricer.get_price_for_day_for_shop",
                        new_callable=AsyncMock,
                    ) as mock_day_price:
                        mock_month_tariff.return_value = 500
                        mock_day_price.return_value = 100

                        # Create ShopMenu instance
                        shop_menu = ShopMenu(
                            bot=mock_bot,
                            chat_id=123456789,
                            state=mock_state,
                            wb_user_cabinet_original_id=1,
                            redis_client=None,
                        )

                        # Initially, token status should not be loaded
                        assert (
                            not shop_menu._token_status_loaded
                        ), "Initially should not be loaded"
                        assert (
                            shop_menu._token_status is None
                        ), "Initially should be None"

                        # Call _load_all_data which should load token status
                        await shop_menu._load_all_data()

                        # Verify that token status was loaded
                        assert (
                            shop_menu._token_status_loaded
                        ), "Should be loaded after _load_all_data()"
                        assert (
                            shop_menu._token_status == sample_token_status_complete
                        ), "Should have correct data"

                        # Verify the service was called
                        mock_token_service.get_shop_token_status.assert_called_once_with(
                            "test_shop_123"
                        )
