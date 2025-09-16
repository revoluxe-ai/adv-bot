import os

import pandas as pd

# Определяем абсолютный путь к файлу requests.csv
current_dir = os.path.dirname(os.path.abspath(__file__))
csv_path = os.path.join(current_dir, 'requests.csv')

# Загружаем данные из CSV в DataFrame
df = pd.read_csv(
    csv_path,
    header=None,
    names=['keyword', 'query']
)

# Преобразуем данные в словарь
queries_dict = df.set_index('keyword')['query'].to_dict()

# Закрываем DataFrame, освобождая память
del df

min_query = list(queries_dict.values())[-1]

def get_queries_of_keyword(keyword: str) -> int | str:
    # Попытка получить значение из словаря
    if keyword in queries_dict:
        return queries_dict[keyword]

    # Возврат значения из последней строки, если ключевое слово отсутствует
    return f'<{min_query}'

