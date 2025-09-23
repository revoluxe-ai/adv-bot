#!/usr/bin/env python3
"""
Быстрая проверка статуса сервиса прогнозирования CTR
"""

import socket
import sys


def check_port(host, port):
    """Проверяет, открыт ли порт"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def main():
    """Основная функция проверки"""
    host = "localhost"
    port = 50051

    print("🔍 Проверка сервиса прогнозирования CTR...")
    print(f"Хост: {host}")
    print(f"Порт: {port}")
    print("-" * 40)

    if check_port(host, port):
        print("✅ Сервис запущен и доступен на порту 50051")
        print("💡 Для полного тестирования запустите: python test_predict_service.py")
        return 0
    else:
        print("❌ Сервис не доступен на порту 50051")
        print("💡 Убедитесь, что run_predict_service.py запущен")
        return 1


if __name__ == "__main__":
    sys.exit(main())
