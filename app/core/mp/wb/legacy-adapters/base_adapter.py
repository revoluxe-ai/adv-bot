from __future__ import annotations

import logging
import time
from typing import Optional, Any, Callable, Dict
from functools import wraps

import httpx

from app.core.mp.wb.protocols.base_wb_protocol import BaseWBAdapterProtocol
from app.core.mp.wb.token_management.factory import get_default_factory
from app.core.mp.wb.token_management.token_context import current_wb_access
from app.core.mp.wb.token_management.enhanced_factory import get_enhanced_factory
from app.core.mp.wb.token_management.enhanced_token_manager import EnhancedShopTokenManager
from app.core.mp.wb.token_management.metrics import record_api_call
from app.core.mp.wb.utils.host_utils import resolve_wb_base_url
from app.shared.domain.protocols.wb_token import WBTokenProtocol

logger = logging.getLogger(__name__)


class BaseWBAdapter(BaseWBAdapterProtocol):
    """Базовый адаптер с общей логикой переключения токенов."""

    def __init__(self, http_client, wb_access=None, token_manager=None, use_enhanced: bool = True):
        self.http_client = http_client
        self.wb_access = wb_access or current_wb_access.get()
        self.use_enhanced = use_enhanced

        if token_manager is not None:
            self._token_manager = token_manager
        elif use_enhanced:
            factory = get_enhanced_factory()
            self._token_manager = factory.get_or_create(self.wb_access)
        else:
            self._token_manager = get_default_factory().get_or_create(self.wb_access)

    @property
    def shop_id(self) -> str:
        return self._token_manager.shop_id

    async def set_next_token(self, method_name: str) -> None:
        """Пометить текущий токен как плохой для метода и переключиться."""
        if isinstance(self._token_manager, EnhancedShopTokenManager):
            current_token = await self._token_manager.get_best_token(method_name)
            if current_token:
                await self._token_manager.mark_token_bad(method_name, current_token.id)
        else:
            token = self._token_manager.current_token
            if not token:
                raise RuntimeError("No current token to mark bad")
            await self._token_manager.mark_token_bad(method_name, token.id)

    async def mark_success(self, method_name: str) -> None:
        """Пометить текущий токен как успешный для метода."""
        if isinstance(self._token_manager, EnhancedShopTokenManager):
            current_token = await self._token_manager.get_best_token(method_name)
            if current_token:
                await self._token_manager.mark_token_success(method_name, current_token.id)
        else:
            # Для обычного менеджера токенов просто логируем успех
            logger.debug(f"Method {method_name} completed successfully")


class BaseAPIAdapter(BaseWBAdapter):
    """Расширенный базовый адаптер с общей логикой для API вызовов."""

    def __init__(self, http_client: httpx.AsyncClient, wb_access=None, api_service: str = None, **kwargs):
        super().__init__(http_client, wb_access, **kwargs)
        self.api_service = api_service  # e.g., "promotion", "content", etc.
        self._generated_clients_cache: Dict[str, Any] = {}

    async def _execute_api_call(
        self,
        method_name: str,
        api_func: Callable,
        retry_on_auth_error: bool = True,
        **api_kwargs
    ) -> Any:
        """
        Универсальный метод для выполнения API вызовов с:
        - Замером времени
        - Обработкой ошибок
        - Retry логикой при ошибках авторизации
        - Записью метрик
        """
        start_time = time.perf_counter()
        
        try:
            client = self._get_or_create_client()
            
            try:
                response = await api_func(client=client, **api_kwargs)
            except Exception as e:
                # Если ошибка авторизации и разрешен retry - пробуем переключить токен
                if retry_on_auth_error and self._is_auth_error(e):
                    logger.warning(f"Auth error in {method_name}, trying to switch token")
                    await self.set_next_token(method_name)
                    client = self._get_or_create_client()
                    response = await api_func(client=client, **api_kwargs)
                else:
                    raise

            # Проверяем, не является ли "успешный" ответ на самом деле ошибкой
            validated_response = self._validate_api_response(response, method_name)
            
            duration = time.perf_counter() - start_time
            record_api_call(self.shop_id, method_name, duration, True)
            await self.mark_success(method_name)
            
            return validated_response
            
        except Exception as e:
            duration = time.perf_counter() - start_time
            record_api_call(self.shop_id, method_name, duration, False)
            
            # Маппим ошибку в понятное исключение
            mapped_error = self._map_api_error(e, method_name)
            logger.error(f"Ошибка в {method_name}: {mapped_error}", exc_info=True)
            raise mapped_error

    def _get_or_create_client(self) -> Any:
        """Получить generated клиент с кешированием по токену."""
        token: WBTokenProtocol = self._token_manager.current_token
        if token is None:
            raise RuntimeError(f"No current token available for {self.api_service} adapter")

        token_key = token.hash
        
        if token_key not in self._generated_clients_cache:
            self._generated_clients_cache[token_key] = self._create_generated_client(token)
            
        return self._generated_clients_cache[token_key]

    def _create_generated_client(self, token: WBTokenProtocol) -> Any:
        """Создать новый generated клиент. Переопределяется в наследниках."""
        raise NotImplementedError("Subclasses must implement _create_generated_client")

    def _is_auth_error(self, error: Exception) -> bool:
        """Определить, является ли ошибка связанной с авторизацией."""
        # Проверяем HTTP статус коды
        if hasattr(error, 'response') and hasattr(error.response, 'status_code'):
            return error.response.status_code in [401, 403]
            
        # Проверяем сообщение об ошибке
        error_msg = str(error).lower()
        return any(keyword in error_msg for keyword in [
            "unauthorized", "401", "forbidden", "403", "authentication", "token"
        ])

    def _map_api_error(self, error: Exception, method_name: str) -> Exception:
        """Маппинг API ошибок в понятные исключения."""
        from app.core.mp.wb.exceptions import (
            WBAuthenticationError,
            WBRateLimitError, 
            WBValidationError,
            WBServerError,
            WBAPIError,
            WBDataProcessingError
        )
        
        # Извлекаем статус код и тело ответа
        status_code = None
        response_body = None
        
        # Обработка ошибок от generated клиентов
        if hasattr(error, 'response'):
            response = error.response
            if hasattr(response, 'status_code'):
                status_code = response.status_code
            if hasattr(response, 'text'):
                response_body = response.text
            elif hasattr(response, 'content'):
                response_body = response.content.decode('utf-8', errors='ignore')
        
        # Проверяем, не является ли ответ объектом ошибки от WB API
        wb_error_details = self._extract_wb_error_details(error)
        if wb_error_details:
            status_code = wb_error_details.get('status', status_code)
            response_body = wb_error_details.get('detail', response_body)
        
        # Маппинг по статус кодам
        if status_code:
            if status_code in [401, 403]:
                return WBAuthenticationError(
                    f"Authentication failed for {method_name}: {response_body or str(error)}"
                )
            elif status_code == 429:
                return WBRateLimitError(
                    f"Rate limit exceeded for {method_name}: {response_body or str(error)}"
                )
            elif status_code in [400, 422]:
                return WBValidationError(
                    f"Validation error in {method_name}: {response_body or str(error)}"
                )
            elif status_code >= 500:
                return WBServerError(
                    f"Server error in {method_name}: {response_body or str(error)}"
                )
        
        # Маппинг по содержимому сообщения
        error_msg = str(error).lower()
        
        if any(keyword in error_msg for keyword in ["timeout", "timed out"]):
            from app.core.mp.wb.exceptions import WBTimeoutError
            return WBTimeoutError(f"Timeout error in {method_name}: {str(error)}")
            
        if any(keyword in error_msg for keyword in ["connection", "network"]):
            from app.core.mp.wb.exceptions import WBConnectionError
            return WBConnectionError(f"Connection error in {method_name}: {str(error)}")
        
        # Общая ошибка API
        return WBAPIError(f"API error in {method_name}: {str(error)}", original_error=error)

    def _extract_wb_error_details(self, error: Exception) -> Optional[Dict[str, Any]]:
        """Извлечь детали ошибки из объектов WB API."""
        # Проверяем, является ли ошибка объектом WB Error Response
        error_obj = None
        
        # Для случаев, когда API возвращает объект ошибки вместо исключения
        if hasattr(error, '__dict__'):
            error_dict = error.__dict__
            
            # Ищем стандартные поля WB API ошибок
            if any(field in error_dict for field in ['status', 'title', 'detail', 'code']):
                return {
                    'status': getattr(error, 'status', None),
                    'title': getattr(error, 'title', None),
                    'detail': getattr(error, 'detail', None),
                    'code': getattr(error, 'code', None),
                    'request_id': getattr(error, 'request_id', None),
                    'origin': getattr(error, 'origin', None),
                }
        
        # Проверяем, есть ли в исключении parsed response
        if hasattr(error, 'response') and hasattr(error.response, 'parsed'):
            parsed = error.response.parsed
            if parsed and hasattr(parsed, 'status'):
                return {
                    'status': getattr(parsed, 'status', None),
                    'title': getattr(parsed, 'title', None),
                    'detail': getattr(parsed, 'detail', None),
                    'code': getattr(parsed, 'code', None),
                }
        
        return None

    def _validate_api_response(self, response: Any, method_name: str) -> Any:
        """Валидация ответа API - проверка, что ответ не содержит ошибку."""
        from app.core.mp.wb.exceptions import WBDataProcessingError
        
        # Если ответ None или пустой - это может быть ошибкой
        if response is None:
            logger.warning(f"Получен пустой ответ от {method_name}")
            return response
        
        # Проверяем, не является ли ответ объектом ошибки WB
        # (иногда WB возвращает объекты ошибок как "успешные" ответы)
        if hasattr(response, 'status') and hasattr(response, 'title'):
            # Это похоже на объект ошибки WB
            status = getattr(response, 'status', None)
            if status and status >= 400:
                error_details = {
                    'status': status,
                    'title': getattr(response, 'title', None),
                    'detail': getattr(response, 'detail', None),
                    'code': getattr(response, 'code', None),
                }
                raise WBDataProcessingError(
                    f"API returned error object in {method_name}: {error_details}"
                )
        
        # Для списков - проверяем, что элементы не являются ошибками
        if isinstance(response, list) and response:
            for item in response[:5]:  # Проверяем только первые 5 элементов
                if hasattr(item, 'status') and hasattr(item, 'title'):
                    status = getattr(item, 'status', None)
                    if status and status >= 400:
                        logger.warning(f"Found error object in response list from {method_name}")
                        break
        
        return response

    def _create_http_client_with_auth(self, base_url: str, token_value: str) -> httpx.AsyncClient:
        """Создать HTTP клиент с авторизацией."""
        auth_headers = dict(self.http_client.headers)
        auth_headers["Authorization"] = f"Bearer {token_value}"
        
        return httpx.AsyncClient(
            base_url=base_url,
            timeout=self.http_client.timeout,
            headers=auth_headers,
        )


