"""Redis менеджер для отслеживания отправленных сообщений пользователям."""

from app.utils.redis_manager import redis_master_client, redis_replica_client


class RedisManager:
    """Менеджер для отслеживания отправленных сообщений в Redis."""

    async def check_message_send(self, message_hash: str, user_id: int, bot_id: int) -> bool:
        """
        Проверяет, было ли сообщение с указанным хэшем отправлено пользователю.

        Args:
            bot_id:  id бота Telegram
            message_hash: SHA256 хэш сообщения
            user_id: ID пользователя Telegram

        Returns:
            True, если сообщение уже было отправлено, False в противном случае
        """
        key = f"message_send:{message_hash}:{user_id}:{bot_id}"
        result = await redis_replica_client.get(key)
        return result is not None

    async def close(self) -> None:
        try:
            await redis_master_client.close()
        except Exception:
            pass
        try:
            await redis_replica_client.close()
        except Exception:
            pass


    async def set_message_send(self, message_hash: str, user_id: int, bot_id: int) -> None:
        """
        Сохраняет факт отправки сообщения пользователю в Redis.

        Args:
            bot_id:
            message_hash: SHA256 хэш сообщения
            user_id: ID пользователя Telegram
        """
        key = self._get_key(message_hash, user_id, bot_id)
        await redis_master_client.set(key, "1")

    @staticmethod
    def _get_key(message_hash: str, user_id: int, bot_id: int):
        return f"message_send:{message_hash}:{user_id}:{bot_id}"


# Экспорт экземпляра для использования в других модулях
redis_manager = RedisManager()


