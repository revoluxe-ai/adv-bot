import json
from typing import Any, Dict

def parse_response_template(template_path: str, replacements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Парсит JSON-файл-шаблон, заменяет заполнители на указанные значения.

    Заполнители в шаблоне должны быть в формате "{{KEY}}".
    Например, "id": "{{ID}}", "name": "{{NAME}}".
    
    Args:
        template_path (str): Путь к файлу шаблона JSON.
        replacements (Dict[str, Any]): Словарь с заменами, где ключ - это KEY из заполнителя,
                                     а значение - это то, на что нужно заменить.

    Returns:
        Dict[str, Any]: Обработанный JSON-объект.
    """
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()

    # Применяем замены к строке шаблона
    for key, value in replacements.items():
        placeholder = f"{{{{{key}}}}}"
        # JSON может содержать строковые значения, которые нужно подставить как строки,
        # но также могут быть числа, которые не должны быть в кавычках.
        # Проще всего заменить на строковое представление и потом распарсить JSON.
        if isinstance(value, (int, float, bool)):
            template_content = template_content.replace(placeholder, str(value))
        else:
            template_content = template_content.replace(placeholder, json.dumps(value))

    # После замены всех плейсхолдеров, парсим строку как JSON
    return json.loads(template_content)
