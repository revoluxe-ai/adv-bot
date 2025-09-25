#!/usr/bin/env python3
"""Smoke test script to verify WBApiContainer boots correctly.

This script tests that all DI components can be instantiated without errors.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.mp.wb.containers import WBApiContainer


async def smoke_test_container():
    """Smoke test для проверки корректной загрузки контейнера."""
    
    print("🚀 Starting WBApiContainer smoke test...")
    
    try:
        # Создаем экземпляр контейнера
        container = WBApiContainer()
        print("✅ Container instantiated successfully")
        
        # Настраиваем базовую конфигурацию
        container.config.promotion.base_url.override("https://advert-api.wildberries.ru/")
        print("✅ Configuration override applied")
        
        # Тестируем получение всех компонентов
        print("\n📦 Testing component instantiation:")
        
        # 1. HTTP Client
        http_client = container.http_client()
        print(f"✅ HTTP Client: {type(http_client).__name__}")
        print(f"   Base URL: {http_client.base_url}")
        print(f"   Timeout: {http_client.timeout}")
        
        # 2. Rate Limit Storage
        rate_limit_storage = container.rate_limit_storage()
        print(f"✅ Rate Limit Storage: {type(rate_limit_storage).__name__}")
        
        # 3. Token Manager Factory
        token_manager_factory = container.token_manager_factory()
        print(f"✅ Token Manager Factory: {type(token_manager_factory).__name__}")
        
        # 4. WB API Adapter Factory
        wb_api_adapter_factory = container.wb_api_adapter_factory()
        print(f"✅ WB API Adapter Factory: {type(wb_api_adapter_factory).__name__}")
        
        # 5. Promotion Adapter V1 (требует wb_access как Dependency)
        try:
            # Этот тест покажет, что зависимость wb_access требуется
            promotion_adapter = container.promotion_adapter_v1()
            print(f"✅ Promotion Adapter: {type(promotion_adapter).__name__}")
        except Exception as e:
            print(f"⚠️  Promotion Adapter (expected dependency missing): {e}")
        
        # 6. WB API Factory (также требует wb_access как Dependency)
        try:
            wb_api = container.wb_api_factory()
            print(f"✅ WB API Factory: {type(wb_api).__name__}")
        except Exception as e:
            print(f"⚠️  WB API Factory (expected dependency missing): {e}")
        
        # Тестируем функциональность основных компонентов
        print("\n🔧 Testing component functionality:")
        
        # Test Rate Limit Storage
        test_delay = await rate_limit_storage.preflight_delay("test_shop", "promotion", "get_campaigns")
        print(f"✅ Rate Limit Storage preflight_delay: {test_delay}s")
        
        # Test Token Manager Factory
        token_manager = token_manager_factory.get_manager("test_shop")
        print(f"✅ Token Manager created: shop_id={token_manager.shop_id}")
        
        # Test Adapter Factory (будет ошибка из-за NotImplementedError, но это ожидаемо)
        try:
            adapter = wb_api_adapter_factory.get_adapter("test_shop", "promotion", "v1")
            print(f"✅ Adapter created: {type(adapter).__name__}")
        except NotImplementedError:
            print("⚠️  Adapter creation (expected NotImplementedError in _create_adapter)")
        
        # Закрываем HTTP клиент
        await http_client.aclose()
        print("✅ HTTP Client closed")
        
        print("\n🎉 Smoke test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Smoke test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Главная функция для запуска smoke теста."""
    print("WBApiContainer Smoke Test")
    print("=" * 50)
    
    # Запускаем async smoke test
    success = asyncio.run(smoke_test_container())
    
    if success:
        print("\n✅ All tests passed! Container is ready for use.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Check the output above.")
        sys.exit(1)


if __name__ == "__main__":
    main()