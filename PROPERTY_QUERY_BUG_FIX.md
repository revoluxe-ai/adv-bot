# Property Query Bug Fix - Complete Resolution

## Bug Summary

**Error:** `TypeError: '<=' not supported between instances of 'property' and 'datetime.datetime'`

**Location:** [_get_expiring_tokens](file://c:\Users\vkita\my_code\tasks\qoder-1\adv-bot\app\modules\token_monitoring\services\token_info_service.py#L252-L296) method in token_info_service.py

**Cause:** Using `WBToken.expires` (a Python property) in SQLAlchemy WHERE clauses

## Root Cause Analysis

### The Problem

The `WBToken.expires` field is a **@property** that decodes JWT tokens to extract expiration dates:

```python
class WBToken(BaseTable):
    @property
    def expires(self):
        return self.__expires
    
    @property
    def __expires(self):
        return datetime.datetime.fromtimestamp(self.__payload.get("exp"))
```

### Why It Failed

SQLAlchemy queries expect **Column objects** in WHERE clauses, not Python properties:

```python
# ❌ PROBLEMATIC CODE (causing TypeError):
stmt = (
    select(WBToken)
    .where(WBToken.shop_id == shop_id)
    .where(WBToken.expires <= cutoff_date)      # Property used in SQL!
    .where(WBToken.expires > datetime.datetime.now())
)
```

**The error occurs because:**
1. `WBToken.expires` is a property (Python method)
2. SQLAlchemy can't translate property logic to SQL
3. Properties contain JWT decoding that must run in Python, not SQL

## The Fix

### Strategy

Move property-based filtering from SQL to Python:

1. **Query**: Get all tokens for the shop (using only columns)
2. **Filter**: Apply property-based conditions in Python

### Implementation

```python
# ✅ FIXED CODE:
async def _get_expiring_tokens(self, session, shop_id, shop_name, days_ahead=14):
    cutoff_date = datetime.datetime.now() + datetime.timedelta(days=days_ahead)
    now = datetime.datetime.now()
    
    # 1. Query only by columns (no properties in WHERE clause)
    stmt = select(WBToken).where(WBToken.shop_id == shop_id)
    result = await session.execute(stmt)
    tokens = list(result.scalars().all())
    
    expiring_tokens = []
    
    # 2. Filter using properties in Python
    for token in tokens:
        try:
            token_expires = token.expires  # Property access in Python
            
            # Apply filtering logic in Python, not SQL
            if token_expires <= cutoff_date and token_expires > now:
                token_info = TokenInfo.from_wb_token(token)
                if token_info.is_valid and not token_info.is_read_only:
                    days_until_expiry = (token_expires - now).days
                    expiring_token = ExpiringToken(
                        token_info=token_info,
                        days_until_expiry=days_until_expiry,
                        shop_name=shop_name
                    )
                    expiring_tokens.append(expiring_token)
        except Exception as e:
            # Handle invalid JWTs gracefully
            logging.warning(f"Skipping token {token.id} due to error: {e}")
            continue
    
    return expiring_tokens
```

### Key Changes

1. **Removed property filters from SQL**: No more `WBToken.expires` in WHERE clauses
2. **Added Python-based filtering**: Property access happens after data is loaded
3. **Added error handling**: Gracefully handle invalid JWT tokens
4. **Maintained functionality**: Same logic, different execution layer

## Test Coverage

Created comprehensive test suite in `test_property_query_bug.py`:

### Test Cases

1. **`test_get_expiring_tokens_with_property_fails`**
   - Verifies the fix works without TypeError
   - Would fail before fix, passes after fix

2. **`test_property_usage_in_sqlalchemy_query_demonstration`**
   - Demonstrates why properties can't be used in SQL
   - Educational test showing the core issue

3. **`test_correct_approach_after_fix`**
   - Tests the proper filtering approach
   - Verifies correct behavior with multiple tokens

4. **`test_explain_the_bug`**
   - Educational documentation of the problem and solution

### Test Results

```
✅ All 4 property query bug tests pass
✅ All 5 existing integration tests still pass  
✅ No regression in existing functionality
```

## Performance Considerations

### Before Fix
- **SQL Query**: Complex with property-based WHERE clauses (failed)
- **Database Load**: Lower (if it worked)

### After Fix  
- **SQL Query**: Simple - only column-based filtering
- **Python Processing**: Property evaluation and filtering
- **Database Load**: Slightly higher (fetches more records)

### Performance Trade-off

- **Cost**: Fetches all tokens for shop, then filters in Python
- **Benefit**: Actually works (vs. crashing with TypeError)
- **Optimization**: For shops with many tokens, could add pagination

## Files Modified

1. **`app/modules/token_monitoring/services/token_info_service.py`**
   - Fixed `_get_expiring_tokens()` method
   - Fixed `_get_shop_tokens()` method  
   - Added proper error handling
   - Added logging import

2. **`tests/modules/token_monitoring/test_property_query_bug.py`** (new)
   - Comprehensive test coverage
   - Reproduces original bug scenario
   - Verifies fix works correctly

## Key Learnings

### SQLAlchemy Best Practices

- ✅ **Use columns in WHERE clauses**: `Model.column_name`
- ❌ **Avoid properties in WHERE clauses**: `Model.property_name`
- ✅ **Apply property logic in Python**: After data is loaded

### When Properties Are Involved

1. **Query by columns only**
2. **Load data into Python**  
3. **Apply property-based filtering in loops**
4. **Handle property access exceptions**

### Error Handling

Always wrap property access in try-catch when properties might fail:

```python
try:
    value = token.property_that_might_fail
    # Use value
except Exception as e:
    logging.warning(f"Skipping item due to: {e}")
    continue
```

## Future Prevention

- **Code Review**: Check for properties in SQLAlchemy queries
- **Testing**: Ensure integration tests call actual methods
- **Linting**: Type checkers can catch these issues
- **Documentation**: Clear distinction between columns and properties

This fix ensures the token monitoring system works reliably while maintaining all existing functionality!