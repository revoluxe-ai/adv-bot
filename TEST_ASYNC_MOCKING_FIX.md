# Test Async Mocking Fix - Final Resolution

## Problem Summary

The integration tests were failing with the error:
```
AttributeError: 'coroutine' object has no attribute 'wb_cabinet'
```

This occurred because the async database operations were not properly mocked, causing coroutine objects to be returned where mock objects were expected.

## Root Cause Analysis

The issue had two parts:

### 1. Incorrect Async Context Manager Mocking

**❌ Original problematic approach:**
```python
mock_sm.return_value.__aenter__.return_value = mock_session
```

This doesn't properly set up the async context manager chain.

### 2. Incorrect Database Result Object Mocking

**❌ Problematic approach:**
```python
mock_result = AsyncMock()
mock_result.scalar_one = AsyncMock(return_value=sample_wb_user_cabinet)
```

The issue here is that `scalar_one()` is a **synchronous** method on the database result object, not an async method.

## The Complete Fix

### 1. Proper Async Context Manager Setup

**✅ Correct approach:**
```python
mock_session = AsyncMock()
mock_context_manager = AsyncMock()
mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
mock_context_manager.__aexit__ = AsyncMock(return_value=None)
mock_sm.return_value = mock_context_manager
```

This properly sets up the entire async context manager chain.

### 2. Proper Database Result Object Mocking

**✅ Correct approach:**
```python
mock_result = MagicMock()  # Result object is not async
mock_result.scalar_one.return_value = sample_wb_user_cabinet  # scalar_one() is sync
mock_session.execute = AsyncMock(return_value=mock_result)  # execute() is async
```

This correctly distinguishes between:
- `session.execute()` - **async method** (uses AsyncMock)
- `result.scalar_one()` - **sync method** (uses MagicMock)

### 3. Proper Async Method Mocking

**✅ For async service methods:**
```python
with patch('Service.async_method', new_callable=AsyncMock) as mock_method:
    mock_method.return_value = expected_value
```

## Files Fixed

1. **tests/modules/modules/token_monitoring/test_token_monitoring.py**
2. **tests/modules/shop_menu/test_shop_menu_token_loading.py**  
3. **tests/modules/shop_menu/test_token_loading_bug_reproduction.py**

## Test Results

After applying the fixes:

```
✅ All 5 tests now pass
✅ No more 'coroutine object has no attribute' errors
✅ Integration tests properly verify token loading functionality
```

## Key Learnings

### Async vs Sync in SQLAlchemy Operations

- **Async**: `session.execute(stmt)` 
- **Sync**: `result.scalar_one()`, `result.scalars().all()`

### Proper Mock Types

- **AsyncMock**: For async methods and async context managers
- **MagicMock**: For sync methods and regular objects

### Test Architecture Principle

The integration tests now properly:
1. ✅ Call actual methods (`_load_all_data()`)
2. ✅ Verify service calls (`get_shop_token_status()`)
3. ✅ Test end-to-end data flow
4. ✅ Avoid manually setting internal state

## Future Reference

When writing async integration tests:

1. **Identify the async boundary** - what's async vs sync
2. **Mock the context manager properly** - use the full chain
3. **Mock return objects correctly** - usually sync
4. **Test the actual integration flow** - don't bypass the real methods

This ensures tests catch real bugs like the original token loading issue!