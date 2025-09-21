# Использование скриптов из папки scripts

В этой директории содержатся скрипты, которые можно запускать как из корня проекта, так и непосредственно из папки `scripts/`.

## Настройка путей

Для корректной работы скриптов используется модуль `set_path.py`, который:

1. Добавляет корень проекта в `sys.path`
2. Изменяет текущую рабочую директорию на корень проекта
3. Предоставляет функцию `get_project_path()` для получения абсолютных путей относительно корня проекта

## Создание нового скрипта

Для создания нового скрипта рекомендуется использовать шаблон `template_script.py`. Пример использования:

```python
# my_new_script.py
# Добавляем настройку пути к корню проекта
try:
    # Пытаемся импортировать напрямую, если скрипт запускается из директории scripts
    from set_path import add_project_root_to_path, get_project_path
except ImportError:
    # Если не получается, пробуем импортировать с использованием полного пути
    from scripts.set_path import add_project_root_to_path, get_project_path

# Добавляем корень проекта в sys.path
project_root = add_project_root_to_path()

# Теперь можно импортировать модули из корня проекта
import dotenv
dotenv.load_dotenv()

# Пример импорта модулей из корня проекта
# from app.modules.some_module import SomeClass
```

## Запуск скриптов

### Из директории scripts

```bash
cd scripts
python my_script.py
```

### Из корня проекта

```bash
python scripts/my_script.py
```

## Работа с путями внутри скриптов

Если в скрипте требуется обращение к файлам по относительным путям, используйте функцию `get_project_path`:

```python
from set_path import get_project_path

# Получение абсолютного пути к файлу относительно корня проекта
config_path = get_project_path('app/config/settings.json')
```

## Тестирование настройки путей

Для проверки корректности настройки путей используйте скрипт `test_path.py`:

```bash
python scripts/test_path.py
```
