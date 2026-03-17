# Bug Fix: Token Validation Network Resilience

## Issue
`_probe_api` returned `False` for both "permission denied" (HTTP 403) and transient network errors (timeouts, DNS failures, etc.). This caused `PermissionStatus.is_available` to return `False`, making valid tokens appear as missing required permissions. Users saw misleading error messages like "Токен не имеет необходимых прав: Контент, Аналитика, Продвижение" when the token actually had those permissions but the Wildberries API was momentarily unreachable.

**Regression**: The old code only validated JWT claims and was resilient to external API outages; this refactor introduced a regression where transient network issues caused valid tokens to be rejected.

## Root Cause
In `app/modules/token_permissions/validator.py`:
- `_probe_api` method returned `False` for **any** failure (line 151-154)
- This included both:
  - HTTP 403 (permission denied) ← **should reject**
  - Network errors (timeout, connection refused, DNS failure) ← **should fall back to JWT**

## Solution
Modified `_probe_api` to return three states:
- `True`: API probe successful (permission verified)
- `False`: HTTP 403 (permission denied - token lacks this permission)
- `None`: Network/transient error (can't verify, fall back to JWT claims)

### Changes Made

#### 1. `app/modules/token_permissions/validator.py`
- Changed `_probe_api` return type from `bool` to `bool | None`
- Added explicit check for HTTP 403 → return `False`
- Changed exception handler to return `None` (network error)
- Added check for other HTTP errors (4xx, 5xx) → return `None` (service issue)

#### 2. `app/modules/token_permissions/dto.py`
- Enhanced `PermissionStatus.is_available` with detailed docstring
- Clarified that `None` from API probe means fall back to JWT claim
- Logic remains: `if api_probe_success is None: return has_jwt_claim`

#### 3. `tests/modules/token_permissions/test_validator.py`
- Updated `test_probe_api_exception` to expect `None` instead of `False`
- Added `test_probe_api_500_error` for server errors → `None`
- Added `test_probe_api_404_error` for not found → `None`
- Added `test_valid_token_network_errors_fallback_to_jwt` for end-to-end scenario
- Added `test_permission_status_is_available_with_network_error` for DTO behavior
- Clarified `test_valid_token_claims_plus_api_mode_failure` as testing 403 specifically

## Test Results
All 21 tests pass:
```
tests/modules/token_permissions/test_validator.py .... 21 passed in 0.40s
```

## Behavior Matrix

| Scenario | API Probe Result | Token With JWT Claims | Outcome |
|----------|------------------|----------------------|---------|
| API returns 200 + Status:OK | `True` | Yes | ✅ Accepted |
| API returns 200 + Status:ERROR | `None` | Yes | ✅ Accepted (API format issue, fallback to JWT) |
| API returns 403 | `False` | Yes | ❌ Rejected (missing permission) |
| Network timeout | `None` | Yes | ✅ Accepted (fallback to JWT) |
| DNS failure | `None` | Yes | ✅ Accepted (fallback to JWT) |
| Connection refused | `None` | Yes | ✅ Accepted (fallback to JWT) |
| API returns 500 | `None` | Yes | ✅ Accepted (service issue, fallback to JWT) |
| API returns 404 | `None` | Yes | ✅ Accepted (service issue, fallback to JWT) |
| No JWT claim | N/A | No | ❌ Rejected (missing claim) |

## Impact
- **Before fix**: Transient network issues caused valid tokens to be rejected → users blocked from using service
- **After fix**: Transient network issues fall back to JWT validation → users can continue working
- **No regression**: HTTP 403 still correctly rejects tokens with insufficient permissions

## Validation Mode
The validator supports two modes:
- `claims_only`: Only validates JWT, no API probes (always resilient)
- `claims_plus_api`: Validates JWT + probes API (now resilient to network errors)

Current usage in handlers: `claims_plus_api` mode (see `app/client_bot/user_interface/handlers/start/start.py`)

## Related Files
- `app/modules/token_permissions/validator.py` - Main validation logic
- `app/modules/token_permissions/dto.py` - Data transfer objects
- `tests/modules/token_permissions/test_validator.py` - Test suite
- `app/client_bot/user_interface/handlers/start/start.py` - Handler that uses validator

## Date
2026-03-13
