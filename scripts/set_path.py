"""
Модуль для настройки путей при запуске скриптов из директории scripts.
Добавляет корень проекта в sys.path, позволяя импортировать модули из корня проекта.
"""

import os
import sys
from pathlib import Path


def add_project_root_to_path():
    """
    Добавляет корень проекта в sys.path, что позволяет скриптам работать как из корня проекта.
    """
    # Получаем абсолютный путь к директории скрипта
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    # Получаем корень проекта (на один уровень выше, чем директория скриптов)
    project_root = script_dir.parent

    # Если корень проекта еще не в sys.path, добавляем его
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"Добавлен путь к корню проекта: {project_root}")

    # Устанавливаем текущую директорию как корень проекта
    os.chdir(project_root)
    print(f"Текущая директория изменена на: {os.getcwd()}")

    return project_root


def get_project_path(relative_path):
    """
    Получает абсолютный путь к файлу относительно корня проекта.

    Args:
        relative_path (str): Относительный путь от корня проекта

    Returns:
        str: Абсолютный путь к файлу
    """
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    project_root = script_dir.parent
    return os.path.join(project_root, relative_path)
