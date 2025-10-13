# Token Access Monitoring System

A comprehensive token monitoring system for the Wildberries advertising bot that provides real-time token status information, automatic deactivation detection, and proactive expiration notifications.

## Features

### 🔍 Token Information Service
- **Permission Aggregation**: Analyzes all tokens for a shop to determine if required rights are available
- **Status Assessment**: Provides "Complete" or "Insufficient" status based on token permissions
- **Expiration Tracking**: Monitors token expiration dates and identifies expiring tokens

### 🚨 Token Deactivation Detection
- **Automatic Detection**: Monitors API calls for token failures and detects when all tokens are deactivated
- **Real-time Notifications**: Sends immediate alerts to users when token deactivation is detected
- **HTTP Decorator Integration**: Seamlessly integrates with existing API retry logic

### ⏰ Proactive Expiration Monitoring
- **Scheduled Checks**: Daily monitoring of token expiration dates
- **Multi-stage Warnings**: Sends notifications at 14 days, 3 days, and 1 day before expiration
- **Duplicate Prevention**: Database constraints prevent duplicate notifications

### 📱 User Notification System
- **Telegram Integration**: Direct integration with the existing bot messaging system
- **Localized Messages**: Russian-language notifications with clear action items
- **Error Handling**: Graceful handling of blocked users and delivery failures

## Architecture

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   TokenInfoService  │    │ TokenMonitoringService │    │ NotificationManager │
│                     │    │                     │    │                     │
│ • Permission check  │    │ • Deactivation     │    │ • Telegram messages│
│ • Status analysis   │    │   detection         │    │ • User management   │
│ • Expiration query  │    │ • HTTP decorator    │    │ • Error handling    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
           │                           │                           │
           └───────────────────────────┼───────────────────────────┘
                                       │
                          ┌─────────────────────┐
                          │TokenExpirationService│
                          │                     │
                          │ • Daily monitoring  │
                          │ • Scheduled checks  │
                          │ • Warning stages    │
                          └─────────────────────┘
```

## Quick Start

### 1. Installation

Add the token monitoring to your application startup:

```python
from app.modules.token_monitoring import install_all_token_monitoring

# In your application startup
install_all_token_monitoring()
```

### 2. Database Migration

Run the migration to create the notification tracking table:

```bash
alembic upgrade head
```

### 3. Basic Usage

```python
from app.modules.token_monitoring import get_shop_token_status

# Get comprehensive token status for a shop
status = await get_shop_token_status("your_shop_id")

print(f"Status: {status.status}")
print(f"Valid tokens: {status.valid_token_count}")
print(f"Has all permissions: {status.has_all_required_permissions}")
```

## API Reference

### TokenInfoService

#### `get_shop_token_status(shop_id: str) -> TokenStatusReport`

Analyzes all tokens for a shop and returns comprehensive status information.

```python
status = await get_shop_token_status("shop_123")

# Status properties
status.status              # "Complete" or "Insufficient"
status.shop_name          # User-defined shop name
status.total_tokens       # Total number of tokens
status.valid_token_count  # Number of valid tokens
status.available_permissions  # Set of available permissions
status.missing_permissions    # Set of missing permissions
status.expiring_tokens       # List of tokens expiring soon
```

#### `validate_permissions(shop_id: str, required_rights: set[str]) -> PermissionValidation`

Validates if a shop has specific permissions available.

```python
validation = await validate_permissions("shop_123", {"Контент", "Статистика"})

validation.has_access           # True if all permissions available
validation.missing_permissions  # Set of missing permissions
validation.error_message       # Human-readable error message
```

### NotificationManager

#### `notify_token_issue(shop_id, notification_type, expiry_date=None)`

Sends token-related notifications to all users of a shop.

```python
from app.modules.token_monitoring.models import NotificationType

# Send deactivation notification
await notify_token_issue(
    shop_id="shop_123",
    notification_type=NotificationType.TOKEN_DEACTIVATED.value
)

# Send expiration warning
await notify_token_issue(
    shop_id="shop_123", 
    notification_type=NotificationType.TOKEN_EXPIRING_14_DAYS.value,
    expiry_date=datetime.now() + timedelta(days=14)
)
```

### TokenExpirationService

#### `check_token_expiration() -> Dict[str, Any]`

Runs a complete token expiration check and sends notifications.

```python
stats = await run_token_expiration_check()

# Statistics
stats['total_tokens_checked']    # Number of tokens examined
stats['expiring_tokens_found']   # Tokens in warning stages
stats['notifications_sent']      # Notifications successfully sent
stats['warnings_by_stage']       # Breakdown by warning stage (14, 3, 1 days)
```

## Configuration

### Required Permissions

The system checks for these required permissions:

- **"Контент"** (Content) - For product management
- **"Статистика"** (Statistics) - For performance data
- **"Аналитика"** (Analytics) - For detailed analytics
- **"Продвижение"** (Promotion) - For advertising campaigns

### Warning Stages

Expiration warnings are sent at:

- **14 days**: Early planning notification
- **3 days**: Urgent preparation warning  
- **1 day**: Critical immediate action required

### Notification Messages

| Type | Message Template |
|------|------------------|
| **Deactivation** | "Токен истек или деактивирован, сделайте срочно новый и добавьте в магазин {shop_name}" |
| **14 Days** | "Токен для магазина {shop_name} истекает через 2 недели ({expiry_date}). Подготовьте новый токен заранее" |
| **3 Days** | "Внимание! Токен для магазина {shop_name} истекает через 3 дня ({expiry_date}). Срочно подготовьте новый токен" |
| **1 Day** | "СРОЧНО! Токен для магазина {shop_name} истекает завтра ({expiry_date}). Добавьте новый токен сегодня" |

## Advanced Usage

### Custom Integration

```python
from app.modules.token_monitoring import (
    initialize_token_monitoring,
    shutdown_token_monitoring
)
from datetime import time

# Custom initialization
await initialize_token_monitoring(
    enable_decorator_monitoring=True,    # Enable deactivation detection
    enable_expiration_scheduler=True,    # Enable proactive monitoring
    daily_check_time=time(10, 30)       # Run checks at 10:30 AM
)

# Graceful shutdown
await shutdown_token_monitoring()
```

### Scheduled Monitoring

```python
from app.modules.token_monitoring.scheduler import TokenMonitoringScheduler

scheduler = TokenMonitoringScheduler()

# Start daily checks at 9:00 AM
await scheduler.start_daily_expiration_check(time(9, 0))

# Run manual check
stats = await scheduler.run_manual_check()

# Get expiring tokens report
report = await scheduler.get_expiring_tokens_report(30)  # Next 30 days
```

### Manual Notifications

```python
from app.modules.token_monitoring.services import (
    notify_token_deactivation,
    notify_token_expiring
)

# Send deactivation alert
await notify_token_deactivation("shop_123")

# Send expiration warning
expiry_date = datetime.now() + timedelta(days=3)
await notify_token_expiring("shop_123", 3, expiry_date)
```

## Database Schema

### TokenNotificationTracker

Tracks sent notifications to prevent duplicates:

| Column | Type | Description |
|--------|------|-------------|
| `id` | Integer | Primary key |
| `shop_id` | String | Shop identifier |
| `user_telegram_id` | BigInteger | Telegram user ID |
| `notification_type` | String | Type of notification |
| `token_expiry_date` | DateTime | Token expiration date (nullable) |
| `sent_at` | DateTime | When notification was sent |
| `resolved_at` | DateTime | When issue was resolved (nullable) |

**Unique Constraint**: `(shop_id, user_telegram_id, notification_type)` prevents duplicate notifications.

## Error Handling

The system handles various error scenarios gracefully:

### Telegram Errors
- **TelegramForbiddenError**: User blocked the bot - notification skipped silently
- **Network errors**: Logged but don't interrupt the monitoring flow

### Database Errors  
- **IntegrityError**: Duplicate notifications prevented by unique constraint
- **Connection errors**: Logged and retried on next scheduled run

### API Errors
- **Token validation failures**: Detected and notifications sent
- **Permission errors**: Tracked and reported in status analysis

## Monitoring and Observability

### Logging

The system provides comprehensive logging:

```python
import logging

# Configure logging level
logging.getLogger('app.modules.token_monitoring').setLevel(logging.INFO)
```

Log levels:
- **INFO**: Successful operations, statistics
- **WARNING**: Token issues, expiring tokens
- **ERROR**: System errors, notification failures
- **DEBUG**: Detailed operation traces

### Statistics

Monitor system health with built-in statistics:

```python
# Expiration check statistics
stats = await run_token_expiration_check()

# Monitor key metrics
total_checked = stats['total_tokens_checked']
notifications_sent = stats['notifications_sent']
error_count = stats['errors']

# Alert on high error rates
if error_count > 0:
    logger.warning(f"Token monitoring errors: {error_count}")
```

## Testing

### Unit Tests

Run the comprehensive test suite:

```bash
pytest tests/token_monitoring/ -v
```

Test coverage includes:
- Token permission analysis
- Notification delivery
- Expiration monitoring
- Error handling scenarios
- Database operations

### Integration Tests

Test complete workflows:

```bash
pytest tests/token_monitoring/test_integration.py -v
```

### Demo Script

See the system in action:

```bash
python examples/token_monitoring_demo.py
```

## Performance Considerations

### Database Optimization

- **Indexes**: Automatic indexes on `shop_id`, `user_telegram_id`, `sent_at`
- **Unique constraints**: Prevent duplicate notifications efficiently
- **Cleanup**: Automatic cleanup of old resolved notifications

### Memory Usage

- **Lazy loading**: Components loaded only when needed
- **Async operations**: Non-blocking notification sending
- **Batch processing**: Efficient handling of multiple tokens

### Rate Limiting

- **Telegram API**: Respects bot API rate limits
- **Database queries**: Optimized queries with proper indexing
- **Background tasks**: Non-blocking scheduled operations

## Migration Guide

### From Manual Token Checking

Replace manual token validation:

```python
# Old approach
def check_tokens_manually():
    # Manual token validation logic
    pass

# New approach  
status = await get_shop_token_status(shop_id)
if status.status == "Insufficient":
    # Handle insufficient permissions
    pass
```

### Existing Notification Systems

Integrate with existing notification infrastructure:

```python
# Use existing bot instance
from app.client_bot.bot import get_bot

notification_manager = NotificationManager(bot=get_bot())
```

## Troubleshooting

### Common Issues

**No notifications sent:**
- Check shop has associated users in WBUserCabinet
- Verify Telegram bot credentials
- Check for TelegramForbiddenError in logs

**Duplicate notifications:**
- Database unique constraint should prevent this
- Check for IntegrityError handling in logs

**Missing token data:**
- Ensure WBToken records have shop_id populated
- Verify token expiration dates are set correctly

### Debug Mode

Enable detailed logging:

```python
import logging

logging.getLogger('app.modules.token_monitoring').setLevel(logging.DEBUG)
```

### Health Checks

Verify system status:

```python
# Check if monitoring is installed
from app.modules.token_monitoring.integration import is_token_monitoring_installed

if not is_token_monitoring_installed():
    logger.warning("Token monitoring not installed")

# Run manual check to verify functionality
stats = await run_token_expiration_check()
logger.info(f"System check: {stats}")
```

## Contributing

When extending the token monitoring system:

1. **Add tests** for new functionality
2. **Update documentation** including this README
3. **Follow error handling patterns** established in existing code
4. **Consider backwards compatibility** for API changes
5. **Test with real data** in development environment

## License

This token monitoring system is part of the Wildberries advertising bot project and follows the same licensing terms.