#!/usr/bin/env python
"""
Скрипт для запуска тестов проверки циклических импортов в точках входа
"""
import subprocess
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
sys.path.insert(0, str(project_root))


def activate_venv():
    """Активирует виртуальное окружение для Windows/Linux"""
    venv_path = project_root / ".venv"

    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate"
        return f"call {activate_script}"
    else:
        activate_script = venv_path / "bin" / "activate"
        return f"source {activate_script}"


def run_circular_imports_tests():
    """Запускает тесты проверки циклических импортов"""
    print("🔍 Проверка циклических импортов в точках входа...")

    # Определение команды для запуска pytest
    # Встраиваем активацию окружения в команду
    cmd = []

    if sys.platform == "win32":
        # Для Windows используем powershell
        cmd = [
            "powershell",
            "-Command",
            ".\\.\\.venv\\Scripts\\activate; python -m pytest tests/test_circular_imports.py -xvs"
        ]
    else:
        # Для Linux/MacOS
        cmd = [
            "/bin/bash",
            "-c",
            "source ./.venv/bin/activate && python -m pytest tests/test_circular_imports.py -xvs"
        ]

    # Запускаем команду
    return subprocess.run(cmd, cwd=project_root)


if __name__ == "__main__":
    result = run_circular_imports_tests()
    sys.exit(result.returncode)
