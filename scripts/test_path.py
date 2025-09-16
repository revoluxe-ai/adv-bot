# test_path.py
# Скрипт для проверки правильной настройки путей

# Добавляем настройку пути к корню проекта
try:
    # Пытаемся импортировать напрямую, если скрипт запускается из директории scripts
    from set_path import add_project_root_to_path, get_project_path
except ImportError:
    # Если не получается, пробуем импортировать с использованием полного пути
    from scripts.set_path import add_project_root_to_path, get_project_path

# Добавляем корень проекта в sys.path
project_root = add_project_root_to_path()

import os
import sys

import pandas as pd


def test_path_configuration():
    """
    Проверяет правильность настройки путей для запуска скриптов из папки scripts.
    """
    # Выводим текущий рабочий каталог
    current_dir = os.getcwd()
    print(f"Текущая директория: {current_dir}")

    # Выводим sys.path
    print("\nПути в sys.path:")
    for path in sys.path:
        print(f" - {path}")

    # Проверяем доступ к файлу в корне проекта
    env_file = os.path.join(current_dir, '.env')
    if os.path.exists(env_file):
        print(f"\nФайл .env найден: {env_file}")
    else:
        print(f"\nФайл .env не найден: {env_file}")

    # Проверяем доступ к CSV файлу в модуле, который вызывал ошибку
    csv_path = get_project_path('app/modules/keywords_query/requests.csv')
    if os.path.exists(csv_path):
        print(f"\nФайл requests.csv найден: {csv_path}")
        # Проверка чтения CSV файла
        try:
            df = pd.read_csv(
                csv_path,
                header=None,
                nrows=5  # Читаем только первые 5 строк для проверки
            )
            print(f"Чтение CSV файла успешно, первые строки:\n{df.head()}")
        except Exception as e:
            print(f"Ошибка при чтении CSV файла: {e}")
    else:
        print(f"\nФайл requests.csv не найден: {csv_path}")

    # Проверяем импорт модуля из app
    try:
        print("\nМодуль keywords_query успешно импортирован")
    except Exception as e:
        print(f"\nОшибка при импорте модуля keywords_query: {e}")

    return True

if __name__ == "__main__":
    test_path_configuration()
