from .http_request import requests
from asyncio import Lock

class OnlyRead:
    TRUE = True
    FALSE = False



locker = Lock()

class Rights:
    CONTENT = 'Контент'
    ANALYTICS = 'Аналитика'
    PRICES_AND_DISCOUNTS = 'Цены и скидки'
    MARKETPLACE = 'Маркетплейс'
    STATISTICS = 'Статистика'
    PROMOTION = 'Продвижение'
    QUESTIONS_AND_REVIEWS = 'Вопросы и отзывы'
    RECOMMENDATIONS = 'Рекомендации'




import aiohttp
import logging


logger = logging.getLogger(__name__)

timeout = aiohttp.ClientTimeout(
    total=3,  # Общий таймаут для запроса
    connect=2,  # Таймаут для подключения
    sock_read=2,  # Таймаут для чтения сокета
    sock_connect=2  # Таймаут для соединения сокета
)


