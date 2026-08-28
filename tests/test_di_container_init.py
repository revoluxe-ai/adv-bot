"""Тест для проверки инициализации DI контейнера.

Инвариант harness (FP-001): Redis FORCE-host в conftest должен совпадать
с PG/CH IPv4 loopback (`127.0.0.1`), иначе на Windows `localhost`→`::1`
ломает ping к compose Redis.
"""

import os

import pytest

from app.core.di.app_container import AppContainer

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_di_container_init():
    """DI init + Redis harness host aligned to PG/CH IPv4 loopback.

    Asserts conftest FORCE-binds REDIS_*HOST to the same host as Postgres
    (not literal ``localhost``), then initializes AppContainer resources
    against compose-mapped Redis/PG/CH.
    """
    pg_host = os.environ["POSTGRES_MASTER_HOST"]
    assert pg_host == "127.0.0.1"
    assert os.environ["REDIS_HOST"] == pg_host
    assert os.environ["REDIS_MASTER_HOST"] == pg_host
    assert os.environ["REDIS_REPLICA_HOST"] == pg_host

    container = AppContainer()

    try:
        await container.init_resources()
        print("✓ DI контейнер инициализирован успешно")
    except Exception as e:
        print(f"✗ Ошибка при инициализации DI контейнера: {e}")
        raise
    finally:
        await container.shutdown_resources()

