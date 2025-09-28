# Token Status Loading Bug - Test Analysis & Fix

## Summary

The user was experiencing a bug where ShopMenu showed "Состояние токенов: ⚠️ Ошибка загрузки" (Token status: ⚠️ Loading error) instead of actual token status information.

## Root Cause

The bug existed because:

1. **Token status was never loaded**: The `_load_all_data()` method didn't call `get_shop_token_status()`
2. **Variables remained uninitialized**: `_token_status_loaded` stayed `False` and `_token_status` stayed `None`
3. **Error message was shown**: The text property showed "Ошибка загрузки" when `_token_status_loaded` was `False`

## Why Tests Didn't Catch This Bug

### The Flawed Testing Approach

The existing tests had a critical flaw - they **manually set** the token status variables instead of testing the actual loading process:

```python
# FLAWED APPROACH (existing tests):
shop_menu._token_status = sample_token_status          # ❌ Manually set
shop_menu._token_status_loaded = True                  # ❌ Manually set
text = shop_menu.text                                   # ✅ Test output
assert "token info" in text                            # ✅ Verify content
```

**Problem**: This approach tests the text formatting but **never verifies that token loading actually works**.

### What Was Missing

The tests should have:

1. **Called actual loading methods**: `_load_all_data()` or `__call__()`
2. **Verified service calls**: Ensured `get_shop_token_status()` was called
3. **Tested integration flow**: End-to-end process from loading to display
4. **Not manually set internal state**: Let the code populate its own variables

## Proper Test Strategy

### Integration Tests That Would Have Caught The Bug

```python
# PROPER APPROACH (new tests):
@pytest.mark.asyncio
async def test_token_status_actually_loaded():
    with patch('get_shop_token_status') as mock_service:
        mock_service.return_value = sample_token_status
        
        shop_menu = ShopMenu(...)
        
        # Initially should not be loaded
        assert shop_menu._token_status_loaded == False
        
        # Call the actual loading method
        await shop_menu._load_all_data()
        
        # Verify loading worked
        assert shop_menu._token_status_loaded == True
        assert shop_menu._token_status is not None
        mock_service.assert_called_once_with("shop_123")
```

### Test Categories Created

1. **`test_shop_menu_token_loading.py`**: Comprehensive integration tests
2. **`test_token_loading_bug_reproduction.py`**: Demonstrates the bug and explains testing flaws
3. **Updated existing test file**: Added proper integration test

## The Fix Applied

```python
# Added to _load_all_data() method:
try:
    shop_id = self._wb_cabinet.shop_id
    logger.debug(f"Загрузка статуса токенов для магазина {shop_id}")
    self._token_status = await get_shop_token_status(shop_id)
    self._token_status_loaded = True
    logger.debug(f"Статус токенов загружен: {self._token_status.status}")
except Exception as token_error:
    logger.error(f"Ошибка при загрузке статуса токенов: {token_error}", exc_info=True)
    self._token_status = None
    self._token_status_loaded = False
```

## Test Requirements for Future

### Must Test Integration Flows

✅ **DO**: Call actual methods that should populate data
✅ **DO**: Verify external service calls are made  
✅ **DO**: Test error handling scenarios
✅ **DO**: Verify end-to-end user experience

❌ **DON'T**: Manually set internal variables
❌ **DON'T**: Skip actual method calls
❌ **DON'T**: Test only text output without verifying data loading
❌ **DON'T**: Assume internal implementation works without testing

### Example Test Template

```python
@pytest.mark.asyncio
async def test_feature_integration():
    # 1. Setup mocks for external dependencies
    with patch('external_service') as mock_service:
        mock_service.return_value = expected_data
        
        # 2. Create object in initial state
        obj = MyClass(...)
        assert obj.data_loaded == False  # Initial state
        
        # 3. Call method that should load data
        await obj.load_data()
        
        # 4. Verify data was loaded properly
        assert obj.data_loaded == True
        assert obj.data is not None
        mock_service.assert_called_once()
        
        # 5. Verify end-user experience
        result = obj.get_result()
        assert "expected content" in result
```

## Conclusion

The bug existed because:
- **Code**: Token status wasn't being loaded in `_load_all_data()`
- **Tests**: Existing tests manually set values instead of testing the loading process

The fix ensures token status is properly loaded, and the new tests would catch similar bugs in the future by testing the actual integration flow rather than just the display logic.