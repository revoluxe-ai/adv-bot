# template_script.py
# Шаблон для создания новых скриптов в папке scripts

# Добавляем настройку пути к корню проекта
try:
    # Пытаемся импортировать напрямую, если скрипт запускается из директории scripts
    from set_path import add_project_root_to_path, get_project_path
except ImportError:
    # Если не получается, пробуем импортировать с использованием полного пути
    from scripts.set_path import add_project_root_to_path

# Добавляем корень проекта в sys.path
project_root = add_project_root_to_path()

# Теперь можно импортировать модули из корня проекта
import dotenv

dotenv.load_dotenv()

# Пример импорта модулей из корня проекта
# from app.modules.some_module import SomeClass
# from models.some_model import SomeModel


def main():
    """
    Основная функция скрипта.
    """
    print(f"Скрипт выполняется с корнем проекта: {project_root}")

    # Пример получения абсолютного пути к файлу относительно корня проекта
    # config_path = get_project_path('app/config/settings.json')
    # print(f"Путь к файлу конфигурации: {config_path}")

    # Тут ваш код


if __name__ == "__main__":
    # Если скрипт асинхронный:
    # import asyncio
    # asyncio.run(main())

    # Если скрипт синхронный:
    main()
