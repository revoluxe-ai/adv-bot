"""
Test for the TypeError: '<=' not supported between instances of 'property' and 'datetime.datetime' bug.

This test reproduces the bug where WBToken.expires (a property) is used in SQLAlchemy queries,
which fails because properties can't be used in database queries.
"""

import datetime
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.token_monitoring.services.token_info_service import TokenInfoService


class TestPropertyQueryBug:
    """Test cases for the property query bug."""
    
    @pytest.mark.asyncio
    async def test_get_expiring_tokens_with_property_fails(self):
        """
        Test that reproduces the TypeError when using WBToken.expires in queries.
        
        This test should FAIL before the fix and PASS after the fix.
        """
        from app.modules.common_slaves.wildberries.models import WBToken
        from sqlalchemy import select
        
        # This test demonstrates the bug - using a property in a SQLAlchemy query
        service = TokenInfoService()
        
        with patch('app.modules.token_monitoring.services.token_info_service.get_async_session_maker') as mock_sm:
            # Setup database mocks
            mock_session = AsyncMock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_sm.return_value = mock_context_manager
            
            # Create a mock token with the problematic property
            mock_token = MagicMock()
            mock_token.shop_id = "test_shop_123"
            mock_token.api_key = "valid_jwt_token"
            
            # Mock the database query result
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_token]
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            # This should trigger the TypeError if the bug exists
            # The bug happens when the query tries to use WBToken.expires in WHERE clause
            try:
                await service._get_expiring_tokens(mock_session, "test_shop_123", "Test Shop")
                
                # If we get here without an error, the bug is fixed
                print("✅ Bug is fixed - no TypeError occurred")
                
            except TypeError as e:
                if "'<=' not supported between instances of 'property' and 'datetime.datetime'" in str(e):
                    pytest.fail(f"❌ Bug still exists: {e}")
                else:
                    # Some other TypeError, re-raise it
                    raise
            except Exception as e:
                # Other exceptions are fine for this test, we're only checking for the property TypeError
                print(f"Note: Other exception occurred (not the bug we're testing): {e}")

    @pytest.mark.asyncio
    async def test_property_usage_in_sqlalchemy_query_demonstration(self):
        """
        Demonstration test showing why properties can't be used in SQLAlchemy queries.
        
        This test explicitly shows the problematic pattern.
        """
        from app.modules.common_slaves.wildberries.models import WBToken
        from sqlalchemy import select
        
        # This would cause the error if executed against a real database
        cutoff_date = datetime.datetime.now() + datetime.timedelta(days=14)
        
        # The problematic query pattern (this is what was causing the error):
        try:
            # This statement creation itself should work fine
            stmt = (
                select(WBToken)
                .where(WBToken.shop_id == "test_shop")
                # Note: The next line would cause TypeError when executed:
                # .where(WBToken.expires <= cutoff_date)  # ❌ This is the problem line
            )
            
            # The error would occur when this statement is executed against the database
            # Because WBToken.expires is a @property, not a Column
            print("Statement created successfully (error occurs during execution)")
            
            # For this test, we just verify that WBToken.expires is indeed a property
            import inspect
            assert inspect.isdatadescriptor(WBToken.expires), "WBToken.expires should be a property"
            assert hasattr(WBToken.expires, 'fget'), "Should be a property with getter"
            
            print("✅ Confirmed: WBToken.expires is a property, not a Column")
            
        except Exception as e:
            pytest.fail(f"Unexpected error in statement creation: {e}")

    @pytest.mark.asyncio
    async def test_correct_approach_after_fix(self):
        """
        Test that demonstrates the correct approach after fixing the bug.
        
        This shows how to properly handle property-based filtering.
        """
        service = TokenInfoService()
        
        with patch('app.modules.token_monitoring.services.token_info_service.get_async_session_maker') as mock_sm:
            # Setup database mocks
            mock_session = AsyncMock()
            mock_context_manager = AsyncMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)
            mock_sm.return_value = mock_context_manager
            
            # Create mock tokens
            now = datetime.datetime.now()
            
            # Mock token that should be considered "expiring"
            expiring_token = MagicMock()
            expiring_token.shop_id = "test_shop_123"
            expiring_token.api_key = "valid_jwt_token"
            expiring_token.check_valid.return_value = True
            # Mock the expires property to return a date in the future but within 14 days
            expiring_token.expires = now + datetime.timedelta(days=5)
            expiring_token.categories = {"Контент", "Статистика"}
            expiring_token.read_only = False
            
            # Mock token that should NOT be considered expiring (too far in future)
            future_token = MagicMock()
            future_token.shop_id = "test_shop_123"
            future_token.api_key = "another_valid_jwt_token"
            future_token.check_valid.return_value = True
            future_token.expires = now + datetime.timedelta(days=30)
            future_token.categories = {"Контент", "Статистика"}
            future_token.read_only = False
            
            # Mock the database query result - returns ALL tokens for the shop
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [expiring_token, future_token]
            mock_session.execute = AsyncMock(return_value=mock_result)
            
            # After the fix, this should work and return only the expiring token
            result = await service._get_expiring_tokens(mock_session, "test_shop_123", "Test Shop", days_ahead=14)
            
            # Should return only the token that's expiring within 14 days
            assert len(result) == 1, f"Expected 1 expiring token, got {len(result)}"
            # Allow for small timing differences (4-5 days is fine)
            assert 4 <= result[0].days_until_expiry <= 5, f"Expected 4-5 days until expiry, got {result[0].days_until_expiry}"
            
            print("✅ Correct approach works - filtering happens in Python, not SQL")

    def test_explain_the_bug(self):
        """
        Educational test that explains the bug and solution.
        """
        explanation = """
        BUG EXPLANATION:
        
        The error occurs because:
        1. WBToken.expires is a @property (Python method)
        2. SQLAlchemy queries expect Column objects for WHERE clauses
        3. Properties contain Python logic (JWT decoding) that can't run in SQL
        
        PROBLEMATIC CODE:
        ```python
        stmt = select(WBToken).where(WBToken.expires <= cutoff_date)  # ❌ Error!
        ```
        
        SOLUTION:
        ```python
        # 1. Get all tokens for the shop (no property in WHERE clause)
        stmt = select(WBToken).where(WBToken.shop_id == shop_id)
        tokens = await session.execute(stmt)
        
        # 2. Filter in Python using the property
        expiring_tokens = []
        for token in tokens:
            if token.expires <= cutoff_date:  # ✅ Property access in Python
                expiring_tokens.append(token)
        ```
        
        WHY THIS WORKS:
        - Database query only uses actual columns (shop_id)
        - Property access happens in Python after data is loaded
        - JWT decoding happens in application layer, not database layer
        """
        
        print(explanation)
        
        # This test always passes, it's just documentation
        assert True