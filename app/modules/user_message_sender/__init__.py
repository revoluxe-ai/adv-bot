"""Public API for user-message sender helpers without import-time side effects."""

__all__ = ["send_messages_to_users"]


async def send_messages_to_users() -> None:
    """Load the sender implementation lazily to avoid import-time runtime setup."""
    from .message_for_not_pay_user_sender import send_messages_to_users as impl

    await impl()
