from typing import Union

import pandas as pd

# Загружаем данные из CSV в DataFrame
df = pd.read_csv(
    'app/modules/keywords_query/requests.csv',
    header=None,
    names=['keyword', 'query']
)

# Преобразуем данные в словарь
queries_dict = df.set_index('keyword')['query'].to_dict()

# Закрываем DataFrame, освобождая память
del df


def get_queries_of_keyword(keyword: str) -> Union[int, str]:
    # Попытка получить значение из словаря
    if keyword in queries_dict:
        return queries_dict[keyword]

    # Возврат значения из последней строки, если ключевое слово отсутствует
    min_query = list(queries_dict.values())[-1]
    return f'<{min_query}'

