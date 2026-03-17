# Bug Fix: HTTP 200 with Status != "OK" Handling

## Issue
When the WB API returns HTTP 200 but the response JSON contains `Status` field with a value other than `"OK"` (e.g., `"ERROR"`, `"MAINTENANCE"`, or any other value), the `_probe_api` method returned `False` — the same value as HTTP 403 (permission denied). 

According to the three-state resilience design established in the original PR:
- `True` = API probe successful (permission verified)
- `False` = **HTTP 403 only** (permission denied - token lacks this permission)
- `None` = transient/service error (can't verify, fall back to JWT claims)

A 200 response with unexpected JSON is **not a permission denial** but rather indicates:
- API format change
- Service degradation
- API maintenance mode
- Unexpected API behavior

Treating it as `False` (permission denied) caused valid tokens to be incorrectly rejected, undermining the PR's resilience design.

## Root Cause
In `app/modules/token_permissions/validator.py` line 150-152 (before fix):

```python
async with session.get(url, headers=headers, timeout=timeout) as resp:
    if resp.status == 200:
        data = await resp.json()
        return data.get("Status") == "OK"  # Returns False if Status != "OK"
```

This returned `False` when `Status != "OK"`, conflating:
- Permission denial (should reject token)
- Service/format issues (should fall back to JWT)

## Solution
Modified `_probe_api` to properly distinguish HTTP 200 with non-OK status from permission denial:

```python
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
```

### Changes Made

1. **`app/modules/token_permissions/validator.py`**
   - Split HTTP 200 handling into two cases:
     - `Status == "OK"` → return `True` (permission verified)
     - `Status != "OK"` → return `None` (transient issue, fall back to JWT)
   - Added logging to track when this occurs

2. **`tests/modules/token_permissions/test_validator.py`**
   - Updated `test_probe_api_failure_wrong_status` to expect `None` instead of `False`
   - Added comprehensive docstring explaining the behavior
   - Added new end-to-end test `test_valid_token_api_format_change_fallback_to_jwt` to verify token remains valid

3. **`BUGFIX_TOKEN_VALIDATION_NETWORK_RESILIENCE.md`**
   - Added "API returns 200 + Status:ERROR" row to behavior matrix
   - Clarified expected behavior for this scenario

## Test Results
All 22 tests pass (one new test added):

```
tests/modules/token_permissions/test_validator.py .... 22 passed in 0.46s
```

## Updated Behavior Matrix

| Scenario | API Probe Result | Token With JWT Claims | Outcome |
|----------|------------------|----------------------|---------|
| API returns 200 + Status:OK | `True` | Yes | ✅ Accepted |
| **API returns 200 + Status:ERROR** | **`None`** | Yes | ✅ **Accepted (API format issue, fallback to JWT)** |
| API returns 403 | `False` | Yes | ❌ Rejected (missing permission) |
| Network timeout | `None` | Yes | ✅ Accepted (fallback to JWT) |
| DNS failure | `None` | Yes | ✅ Accepted (fallback to JWT) |
| Connection refused | `None` | Yes | ✅ Accepted (fallback to JWT) |
| API returns 500 | `None` | Yes | ✅ Accepted (service issue, fallback to JWT) |
| API returns 404 | `None` | Yes | ✅ Accepted (service issue, fallback to JWT) |
| No JWT claim | N/A | No | ❌ Rejected (missing claim) |

## Impact

### Before Fix
- HTTP 200 with `Status != "OK"` → `False` (permission denied)
- Valid tokens rejected during API format changes or service issues
- Users blocked from using service unnecessarily

### After Fix
- HTTP 200 with `Status != "OK"` → `None` (transient error)
- Falls back to JWT validation
- Service remains available during API issues
- Only actual permission denials (HTTP 403) reject tokens

## Real-World Scenarios

This fix handles:

1. **API Maintenance Mode**
   - WB API returns 200 with `{"Status": "MAINTENANCE"}`
   - Before: Token rejected → users locked out
   - After: Falls back to JWT → users can continue working

2. **API Format Changes**
   - WB changes response format, returns 200 with different Status values
   - Before: All tokens rejected until code update
   - After: Falls back to JWT → service continues functioning

3. **Service Degradation**
   - API returns 200 but with error status due to backend issues
   - Before: Valid tokens incorrectly flagged as missing permissions
   - After: System resilient to API service issues

## Related Files
- `app/modules/token_permissions/validator.py` - Main validation logic
- `app/modules/token_permissions/dto.py` - Data transfer objects
- `tests/modules/token_permissions/test_validator.py` - Test suite
- `BUGFIX_TOKEN_VALIDATION_NETWORK_RESILIENCE.md` - Original PR documentation

## Date
2026-03-13 (fix applied)

## Relates To
This fix completes the three-state resilience design introduced in the original token validation network resilience PR. The original PR handled network errors but missed the edge case of HTTP 200 with non-OK status.
