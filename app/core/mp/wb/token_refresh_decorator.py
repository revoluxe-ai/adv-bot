import logging
from functools import wraps

logger = logging.getLogger(__name__)


def token_refresh_decorator(method):
    @wraps(method)
    async def wrapper(self, shop_id, *args, **kwargs):
        # Получаем клиента через фабрику
        client = await self.client_factory.get_client(shop_id)
        try:
            return await method(self, shop_id, *args, client=client, **kwargs)
        except Exception as e:
            # Проверяем, что это ошибка токена (401)
            if hasattr(e, 'status_code') and e.status_code == 401:
                logger.warning(f"Токен невалиден для магазина {shop_id}, обновляю токены...")
                await self.client_factory.token_manager.mark_token_invalid(
                    self.client_factory._section, shop_id, client.token
                )
                await self.client_factory.token_manager.refresh_tokens(
                    self.client_factory._section, shop_id, self.client_factory._fetch_tokens_func
                )
                # Пробуем ещё раз с новым клиентом
                client = await self.client_factory.get_client(shop_id)
                return await method(self, shop_id, *args, client=client, **kwargs)
            raise

    return wrapper
