"""
Demo script showing how to use the Token Monitoring System.

This script demonstrates the main features of the token monitoring system:
1. Token status analysis and permission checking
2. Proactive expiration monitoring  
3. Token deactivation detection and notifications
4. Scheduled monitoring setup

Run this script to see the token monitoring system in action.
"""

import asyncio
import datetime
import logging
from datetime import time

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def demo_token_status_analysis():
    """Demonstrate token status analysis and permission checking."""
    logger.info("=== Token Status Analysis Demo ===")
    
    try:
        from app.modules.token_monitoring.services import (
            get_shop_token_status,
            validate_shop_permissions,
            REQUIRED_RIGHTS
        )
        
        # Example shop ID (replace with actual shop ID from your database)
        shop_id = "example_shop_123"
        
        # Get comprehensive token status for a shop
        logger.info(f"Analyzing token status for shop: {shop_id}")
        
        status_report = await get_shop_token_status(shop_id)
        
        logger.info(f"Shop: {status_report.shop_name}")
        logger.info(f"Status: {status_report.status}")
        logger.info(f"Total tokens: {status_report.total_tokens}")
        logger.info(f"Valid tokens: {status_report.valid_token_count}")
        logger.info(f"Has all required permissions: {status_report.has_all_required_permissions}")
        
        if status_report.missing_permissions:
            logger.warning(f"Missing permissions: {', '.join(status_report.missing_permissions)}")
        
        if status_report.expiring_tokens:
            logger.warning(f"Expiring tokens: {len(status_report.expiring_tokens)}")
            for token in status_report.expiring_tokens:
                logger.warning(
                    f"  Token {token.token_info.id} expires in {token.days_until_expiry} days"
                )
        
        # Validate specific permissions
        logger.info("\\nValidating specific permissions...")
        
        validation = await validate_shop_permissions(shop_id, {"Контент", "Статистика"})
        
        if validation.has_access:
            logger.info("✓ Shop has required permissions for content and statistics")
        else:
            logger.warning(f"✗ Missing permissions: {', '.join(validation.missing_permissions)}")
        
    except Exception as e:
        logger.error(f"Error in token status analysis: {e}")


async def demo_expiration_monitoring():
    """Demonstrate proactive token expiration monitoring."""
    logger.info("\\n=== Token Expiration Monitoring Demo ===")
    
    try:
        from app.modules.token_monitoring.services import (
            run_token_expiration_check,
            get_expiring_tokens_summary
        )
        
        # Run a manual expiration check
        logger.info("Running manual token expiration check...")
        
        stats = await run_token_expiration_check()
        
        logger.info(f"Expiration check results:")
        logger.info(f"  Tokens checked: {stats['total_tokens_checked']}")
        logger.info(f"  Expiring tokens found: {stats['expiring_tokens_found']}")
        logger.info(f"  Notifications sent: {stats['notifications_sent']}")
        logger.info(f"  Notifications skipped: {stats['notifications_skipped']}")
        logger.info(f"  Errors: {stats['errors']}")
        
        for stage in [14, 3, 1]:
            if stats['warnings_by_stage'][stage] > 0:
                logger.info(f"  {stage}-day warnings: {stats['warnings_by_stage'][stage]}")
        
        # Get summary of expiring tokens
        logger.info("\\nGetting expiring tokens summary...")
        
        summary = await get_expiring_tokens_summary(30)
        
        logger.info(f"Tokens expiring in next 30 days: {summary['total_expiring']}")
        
        for days in ["1", "3", "7", "14", "30"]:
            count = len(summary['by_days'][days])
            if count > 0:
                logger.info(f"  Expiring in {days} day(s): {count} tokens")
        
        if summary['by_shop']:
            logger.info("\\nBy shop:")
            for shop_id, shop_data in summary['by_shop'].items():
                token_count = len(shop_data['tokens'])
                earliest = shop_data['earliest_expiry'].strftime('%Y-%m-%d')
                logger.info(f"  {shop_id}: {token_count} tokens, earliest expires {earliest}")
    
    except Exception as e:
        logger.error(f"Error in expiration monitoring: {e}")


async def demo_notification_system():
    """Demonstrate the notification system."""
    logger.info("\\n=== Notification System Demo ===")
    
    try:
        from app.modules.token_monitoring.services import (
            NotificationManager,
            notify_token_deactivation,
            notify_token_expiring
        )
        from app.modules.token_monitoring.models import NotificationType
        
        # Note: These are demonstration calls - they will send actual notifications
        # if you have valid shop IDs and user data in your database
        
        # Example shop ID (replace with actual shop ID)
        shop_id = "example_shop_123"
        
        logger.info(f"Demonstration of notification types for shop: {shop_id}")
        logger.info("(Note: Actual notifications will only be sent if shop has valid users)")
        
        # Create notification manager
        notification_manager = NotificationManager()
        
        # Example 1: Token deactivation notification
        logger.info("\\n1. Token deactivation notification")
        # Uncomment to send actual notification:
        # await notify_token_deactivation(shop_id, context={"method": "demo"})
        logger.info("  Message would be: 'Токен истек или деактивирован, сделайте срочно новый...'")
        
        # Example 2: Token expiring notifications
        logger.info("\\n2. Token expiring notifications")
        
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=14)
        # Uncomment to send actual notification:
        # await notify_token_expiring(shop_id, 14, expiry_date)
        logger.info(f"  14-day warning: 'Токен истекает через 2 недели ({expiry_date.strftime('%d.%m.%Y')})'")
        
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=3)
        # Uncomment to send actual notification:
        # await notify_token_expiring(shop_id, 3, expiry_date)
        logger.info(f"  3-day warning: 'Внимание! Токен истекает через 3 дня...'")
        
        expiry_date = datetime.datetime.now() + datetime.timedelta(days=1)
        # Uncomment to send actual notification:
        # await notify_token_expiring(shop_id, 1, expiry_date)
        logger.info(f"  1-day warning: 'СРОЧНО! Токен истекает завтра...'")
        
        # Example 3: Get notification history
        logger.info("\\n3. Notification history")
        
        history = await notification_manager.get_notification_history(shop_id, limit=5)
        logger.info(f"Recent notifications for shop: {len(history)}")
        
        for notification in history:
            logger.info(
                f"  {notification.sent_at.strftime('%Y-%m-%d %H:%M')} - "
                f"{notification.notification_type} - "
                f"User: {notification.user_telegram_id} - "
                f"Resolved: {notification.is_resolved}"
            )
    
    except Exception as e:
        logger.error(f"Error in notification demo: {e}")


async def demo_scheduler_setup():
    """Demonstrate setting up scheduled monitoring."""
    logger.info("\\n=== Scheduler Setup Demo ===")
    
    try:
        from app.modules.token_monitoring.scheduler import (
            TokenMonitoringScheduler,
            get_token_monitoring_scheduler
        )
        
        # Get the global scheduler instance
        scheduler = get_token_monitoring_scheduler()
        
        logger.info("Setting up token monitoring scheduler...")
        
        # Configure to run daily at 9:00 AM
        daily_check_time = time(9, 0)
        
        # Start the scheduler (this will run in background)
        logger.info(f"Starting daily expiration check at {daily_check_time}")
        
        # Note: In a real application, this would run continuously
        # For demo purposes, we'll just show the setup
        # await scheduler.start_daily_expiration_check(daily_check_time)
        
        logger.info("Scheduler would now run daily expiration checks")
        logger.info("Each day at 9:00 AM, the system would:")
        logger.info("  1. Check all active tokens for expiration")
        logger.info("  2. Send notifications for tokens expiring in 14, 3, or 1 days")
        logger.info("  3. Avoid duplicate notifications using database constraints")
        logger.info("  4. Log statistics about the check")
        
        # Run a manual check to show what would happen
        logger.info("\\nRunning manual check to demonstrate...")
        
        stats = await scheduler.run_manual_check()
        
        logger.info("Manual check completed:")
        logger.info(f"  Tokens checked: {stats.get('total_tokens_checked', 0)}")
        logger.info(f"  Notifications sent: {stats.get('notifications_sent', 0)}")
        
        # Get expiring tokens report
        logger.info("\\nGetting expiring tokens report...")
        
        report = await scheduler.get_expiring_tokens_report(30)
        logger.info(f"Tokens expiring in next 30 days: {report['total_expiring']}")
        
        # Note: To stop the scheduler in a real application:
        # await scheduler.stop()
        
    except Exception as e:
        logger.error(f"Error in scheduler demo: {e}")


async def demo_integration_setup():
    """Demonstrate setting up the complete token monitoring integration."""
    logger.info("\\n=== Integration Setup Demo ===")
    
    try:
        from app.modules.token_monitoring import (
            install_all_token_monitoring,
            initialize_token_monitoring,
            shutdown_token_monitoring
        )
        from app.modules.token_monitoring.integration import (
            is_token_monitoring_installed
        )
        
        logger.info("Setting up complete token monitoring system...")
        
        # Method 1: Quick setup with defaults
        logger.info("\\n1. Quick setup (recommended for most applications):")
        logger.info("   install_all_token_monitoring()")
        logger.info("   This enables:")
        logger.info("   ✓ HTTP decorator monitoring for token deactivation")
        logger.info("   ✓ Daily expiration checks at 9:00 AM")
        logger.info("   ✓ Automatic notifications to users")
        
        # Method 2: Custom setup
        logger.info("\\n2. Custom setup:")
        logger.info("   await initialize_token_monitoring(")
        logger.info("       enable_decorator_monitoring=True,")
        logger.info("       enable_expiration_scheduler=True,")
        logger.info("       daily_check_time=time(10, 30)  # 10:30 AM")
        logger.info("   )")
        
        # Check installation status
        installed = is_token_monitoring_installed()
        logger.info(f"\\nCurrent installation status: {'Installed' if installed else 'Not installed'}")
        
        # Method 3: Graceful shutdown
        logger.info("\\n3. Graceful shutdown:")
        logger.info("   await shutdown_token_monitoring()")
        logger.info("   This safely stops all monitoring components")
        
        logger.info("\\nIntegration points in your application:")
        logger.info("1. Application startup: Call install_all_token_monitoring()")
        logger.info("2. Application shutdown: Call shutdown_token_monitoring()")
        logger.info("3. Manual checks: Use run_token_expiration_check()")
        logger.info("4. Status queries: Use get_shop_token_status(shop_id)")
        
    except Exception as e:
        logger.error(f"Error in integration demo: {e}")


async def main():
    """Run the complete token monitoring demonstration."""
    logger.info("🚀 Starting Token Monitoring System Demo")
    logger.info("=" * 50)
    
    try:
        # Run all demonstration functions
        await demo_token_status_analysis()
        await demo_expiration_monitoring()
        await demo_notification_system()
        await demo_scheduler_setup()
        await demo_integration_setup()
        
        logger.info("\\n" + "=" * 50)
        logger.info("✅ Token Monitoring System Demo Completed Successfully!")
        logger.info("\\nNext steps:")
        logger.info("1. Add install_all_token_monitoring() to your app startup")
        logger.info("2. Add shutdown_token_monitoring() to your app shutdown")
        logger.info("3. Run the migration to create the TokenNotificationTracker table")
        logger.info("4. Test with real shop IDs and tokens in your environment")
        
    except Exception as e:
        logger.error(f"Demo failed with error: {e}")
        logger.error("This is likely due to missing database configuration or test data")
        logger.info("\\nTo run this demo successfully:")
        logger.info("1. Ensure your database is configured and accessible")
        logger.info("2. Run the TokenNotificationTracker migration")
        logger.info("3. Have some test WBToken data in your database")
        logger.info("4. Configure your Telegram bot credentials")


if __name__ == "__main__":
    # Run the demo
    asyncio.run(main())