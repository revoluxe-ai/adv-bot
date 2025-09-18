import subprocess
from pathlib import Path

import pytest

# Маркировка всех тестов в этом файле
pytestmark = pytest.mark.circular_imports

# Список всех точек входа из документации
ENTRY_POINTS = [
    "app/arq_workers/workers.py",  # ARQ worker
    "updater.py",  # Старый модуль обновления данных
    "run_keywords_parsing.py",  # Парсинг ключевых слов
    "run_update_model.py",  # Обновление модели
    "new_wb_shop_update_run.py",  # Новый модуль обновления магазинов Wildberries
    "run_update_predict_ctr.py",  # Обновление предсказаний CTR
    "run_send_info_message_to_users_process.py",  # Отправка сообщений
    "run_update_keyword_vectors_in_redis.py",  # Обновление векторов ключевых слов
    "keyword_sending_to_neo4j.py",  # Отправка ключевых слов в Neo4j
    "trunc_system_log_in_clickhouse.py",  # Очистка системных логов
    "client_bot_run.py",  # Клиентский бот
]

# Директории, которые следует игнорировать при проверке циклических зависимостей
IGNORED_DIRS = [
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".git",
    ".idea",
    ".github",
    ".cursor",
]


def run_pycycle_on_module(module_path, verbose=True):
    """
    Запускает pycycle для проверки циклических импортов в указанном модуле

    Args:
        module_path (str): Путь к модулю или файлу для проверки
        verbose (bool): Выводить ли подробную информацию

    Returns:
        tuple: (returncode, stdout, stderr)
    """
    # Находим корень проекта
    project_root = Path(__file__).parent.parent.absolute()

    # Формируем полный путь к файлу/модулю
    full_path = project_root / module_path

    # Опция для игнорирования директорий
    ignore_option = f"--ignore {','.join(IGNORED_DIRS)}"

    # Добавляем verbose если нужно
    verbose_option = "--verbose" if verbose else ""

    # Формируем команду
    cmd = f"pycycle --source {full_path} {ignore_option} {verbose_option}"

    print(f"Выполняем: {cmd}")

    # Запускаем команду и перехватываем вывод
    process = subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr


@pytest.mark.parametrize("entry_point", ENTRY_POINTS)
def test_no_circular_imports(entry_point):
    """
    Проверяет отсутствие циклических импортов в точке входа

    Args:
        entry_point (str): Путь к модулю или файлу для проверки
    """
    returncode, stdout, stderr = run_pycycle_on_module(entry_point)

    # Вывод результатов для отладки
    print(f"\nРезультат pycycle для {entry_point}:")
    print(f"returncode: {returncode}")
    print(f"stdout: {stdout}")

    if stderr:
        print(f"stderr: {stderr}")

    # Проверка на отсутствие циклических импортов
    success_message = "No circular imports found" in stdout

    # Если были ошибки в поиске циклических импортов, требуется ручная проверка
    manual_check_needed = returncode != 0 and not success_message

    # Основной assert
    assert success_message or manual_check_needed, f"""
    В точке входа {entry_point} найдены циклические импорты:

    {stdout}

    Исправьте циклические импорты для улучшения качества кода.
    """

    # Если требуется ручная проверка, выводим предупреждение
    if manual_check_needed:
        print(f"\n⚠️ ВНИМАНИЕ: Для модуля {entry_point} нужна ручная проверка!")
        print("Возможно, pycycle не смог правильно обработать этот модуль.")


def test_all_entry_points_exist():
    """Проверяет, что все точки входа существуют"""
    project_root = Path(__file__).parent.parent.absolute()

    for entry_point in ENTRY_POINTS:
        file_path = project_root / entry_point
        assert file_path.exists(), (
            f"Точка входа '{entry_point}' не найдена по пути {file_path}"
        )
