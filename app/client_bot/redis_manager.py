from redis.asyncio import Redis
import json
from pydantic import ValidationError
from typing import Optional, Any
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

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
