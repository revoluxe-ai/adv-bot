import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

# Настраиваем переменные окружения для тестов
os.environ["PYTHONPATH"] = str(project_root)


def pytest_configure(config) -> None:
    """
    Конфигурация pytest для корректного поиска и запуска тестов
    """
    # Добавляем метки для тестов
    config.addinivalue_line("markers", "unit: маркирует unit-тесты")
    config.addinivalue_line("markers", "integration: маркирует интеграционные тесты")


# @pytest_asyncio.fixture(scope="function", name="postgres_sqlalchemy_session")
# async def postgres_sqlalchemy_session() -> AsyncGenerator[AsyncSession, None]:
#     """
#     Фикстура для создания сессии SQLAlchemy с использованием PostgreSQL
#     """
#     async with sm() as session:
#         yield session
#         await session.close()
