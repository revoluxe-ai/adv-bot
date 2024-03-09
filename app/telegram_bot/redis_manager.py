from redis.asyncio import Redis
import json
from pydantic import ValidationError
from typing import Optional, Any
import logging
from datetime import datetime
from .last_message import LastMessage

logger = logging.getLogger(__name__)

# class User(BaseModel):
#     id: int
#     is_bot: bool
#     first_name: str
#     last_name: Optional[str]
#     username: Optional[str]
#     language_code: Optional[str]



#
# class Chat(BaseModel):
#     id: int



# class LastMessage(BaseModel):
#     message_id: int
#     content_type: str
#     date: str
#     chat: Chat
#     from_user: User





redis_manaeger = None

class RedisManager:
    _instance = None
    _redis_conn = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_connection(self):
        if self._redis_conn is None:
            self._redis_conn = await Redis.from_url('redis://localhost/0')
        return self._redis_conn

    async def get_last_message(self, chat_id: int) -> Optional[LastMessage]:
        conn = await self.get_connection()
        key = f"chat:{chat_id}:last_message"
        value = await conn.get(key)
        if value is None:
            return None
        decoded_string = value.decode('utf-8')
        # Десериализация данных из JSON
        try:
            message = LastMessage.model_validate_json(decoded_string)
        except ValidationError as e:
            logger.error(f"Ошибка валидации данных: {e.json()}")
            return None
        return message


    async def set_last_message(self, message: LastMessage, message_type: str):
        def to_dict(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [to_dict(item) for item in obj]
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, "__dict__"):
                # Пропускаем приватные атрибуты и методы, а также атрибуты, начинающиеся с "_"
                return {key: to_dict(value) for key, value in obj.__dict__.items() if
                        not key.startswith('_') and not callable(value)}
            elif isinstance(obj, (int, str, float, bool, type(None))):
                return obj
            else:
                return str(obj)

        chat_id = message.chat.id
        message = to_dict(message)
        message['message_type'] = message_type
        message = json.dumps(message)
        conn = await self.get_connection()
        key = f"chat:{chat_id}:last_message"
        await conn.set(key, message)

