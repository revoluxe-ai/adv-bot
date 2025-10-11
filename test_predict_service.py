#!/usr/bin/env python3
"""
Простой тест для проверки работы сервиса прогнозирования CTR
"""

import asyncio
import logging

import grpc  # type: ignore

from app.modules.grpcs.predict_ctr_service.grpc_service.predict_ctr_service_pb2 import (
    PredictCtrRequest,
)
from app.modules.grpcs.predict_ctr_service.grpc_service.predict_ctr_service_pb2_grpc import (
    CtrServiceStub,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_predict_service():
    """Тестирует работу gRPC сервиса прогнозирования"""

    # Параметры подключения
    host = "localhost"
    port = 50051

    try:
        # Создаем канал и клиент
        async with grpc.aio.insecure_channel(f"{host}:{port}") as channel:
            stub = CtrServiceStub(channel)

            # Тестовые данные пользователя
            test_nmids = [493134345]  # Артикул пользователя
            test_phrases = [
                "spf купальник женский большой размер"
            ]  # Ключевое слово пользователя

            print("Отправляем запрос на прогнозирование...")
            print(f"NMID: {test_nmids}")
            print(f"Фраза: {test_phrases}")

            # Создаем запрос
            request = PredictCtrRequest(nmids=test_nmids, phrases=test_phrases)

            # Отправляем запрос
            response = await stub.PredictCtr(request)

            # Выводим результаты
            print("✓ Сервис отвечает!")
            print(f"Получено предсказаний: {len(response.predictions)}")
            print(response.predictions)
            assert response.predictions
            for nmid, phrase in zip(test_nmids, test_phrases):
                key = f"{nmid}_{phrase}"
                if key in response.predictions:
                    ctr = response.predictions[key]
                    print("CTR:", ctr)
                    assert ctr
                    print(f"🎯 NMID {nmid}, фраза '{phrase}': CTR = {ctr:.4f}")
                    print(f"📊 CTR в процентах: {ctr * 100:.2f}%")
                else:
                    logger.warning(
                        f"❌ Нет предсказания для NMID {nmid}, фраза '{phrase}'"
                    )

            return True

    except grpc.aio.AioRpcError as e:
        logger.error(f"Ошибка gRPC: {e.code()}: {e.details()}")
        return False
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}")
        return False


async def test_service_health():
    """Проверяет доступность сервиса"""

    host = "localhost"
    port = 50051

    try:
        # Пытаемся подключиться к сервису
        async with grpc.aio.insecure_channel(f"{host}:{port}") as channel:
            # Простой тест подключения
            await channel.channel_ready()
            print("✓ Сервис доступен и отвечает на подключения")
            return True

    except Exception as e:
        logger.error(f"✗ Сервис недоступен: {e}")
        return False


async def main():
    """Основная функция тестирования"""

    print("=== Тест сервиса прогнозирования CTR ===")
    print("Тестируем с данными пользователя:")
    print("Артикул: 81316895")
    print("Ключевое слово: черные короткие брюки женские")
    print("=" * 50)

    # Проверяем доступность сервиса
    print("1. Проверка доступности сервиса...")
    if not await test_service_health():
        logger.error(
            "Сервис недоступен. Убедитесь, что run_predict_service.py запущен."
        )
        return

    # Тестируем прогнозирование
    print("2. Тест прогнозирования...")
    if await test_predict_service():
        print("✓ Все тесты прошли успешно!")
    else:
        logger.error("✗ Тесты не прошли")


if __name__ == "__main__":
    asyncio.run(main())
