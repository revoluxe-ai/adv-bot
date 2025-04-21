import pytest
from unittest.mock import AsyncMock, patch
import datetime
from app.modules.wb_keywords_parser.wb_parser.parser import ParserService, TotalPages, DataError
from app.modules.common_slaves.wildberries.models import WBItemPosition

@pytest.mark.asyncio
async def test_parse_keywords_from_wb():
    """
    Тест проверяет корректность парсинга ключевых слов из WB
    """
    # Подготовка тестовых данных
    mock_response = {
        'payloadVersion': 2,
        'metadata': {
            'catalog_type': 'merger',
            'catalog_value': 'preset=12345',
            'normquery': 'test_query'
        },
        'data': {
            'total': 100,
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1,
                        'promoPosition': 1,
                        'tp': 'c'  # тип рекламы - поиск
                    }
                },
                {
                    'id': 67890,
                    'log': {
                        'advertId': 'test_adv_id_2',
                        'cpm': 150,
                        'position': 2,
                        'promoPosition': 2,
                        'tp': 'b'  # тип рекламы - автоматическая
                    }
                },
                {
                    'id': 11111,  # товар без рекламы
                }
            ]
        }
    }

    # Создаем мок для метода __parse_keywords_from_wb
    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        # Настраиваем мок для возврата тестовых данных
        mock_parse.return_value = (
            mock_response['data']['products'],
            mock_response['metadata']['normquery'],
            int(mock_response['metadata']['catalog_value'].split('=')[1]),
            mock_response['data']['total']
        )

        # Создаем экземпляр парсера и вызываем тестируемый метод
        parser = ParserService()
        total_pages = TotalPages()
        result = await parser.parse_keywords_from_wb('test_query', 1, total_pages)

        # Проверяем результаты
        assert len(result) == 3  # Должно быть 3 позиции
        
        # Проверяем первую позицию (рекламная, тип - поиск)
        assert result[0].nmid == 12345
        assert result[0].adv_id == 'test_adv_id'
        assert result[0].cpm == 100
        assert result[0].base_position == 1
        assert result[0].promo_position == 1
        assert result[0].adv_type == 9  # тип рекламы - поиск
        
        # Проверяем вторую позицию (рекламная, тип - автоматическая)
        assert result[1].nmid == 67890
        assert result[1].adv_id == 'test_adv_id_2'
        assert result[1].cpm == 150
        assert result[1].base_position == 2
        assert result[1].promo_position == 2
        assert result[1].adv_type == 8  # тип рекламы - автоматическая
        
        # Проверяем третью позицию (без рекламы)
        assert result[2].nmid == 11111
        assert result[2].adv_id is None
        assert result[2].cpm is None
        assert result[2].adv_type is None
        
        # Проверяем общие параметры
        assert total_pages.total_pages == 2  # 100 товаров / 100 на страницу + 1
        assert mock_parse.call_count == 1  # Метод должен быть вызван один раз

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_empty_response():
    """
    Тест проверяет обработку пустого ответа от сервера
    """
    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        # Настраиваем мок для возврата пустых данных
        mock_parse.return_value = (None, None, None, None)

        parser = ParserService()
        total_pages = TotalPages()
        result = await parser.parse_keywords_from_wb('test_query', 1, total_pages)

        assert result == []  # Должен вернуться пустой список
        assert mock_parse.call_count == 1  # Метод должен быть вызван один раз 

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_merger_catalog():
    """
    Тест проверяет парсинг при catalog_type = 'merger'
    В этом случае cluster = text запроса
    """
    mock_response = {
        'payloadVersion': 2,
        'metadata': {
            'catalog_type': 'merger',
            'normquery': 'test_query'
        },
        'data': {
            'total': 100,
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1,
                        'promoPosition': 1,
                        'tp': 'c'
                    }
                }
            ]
        }
    }

    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        # В случае merger, preset = hash(text)
        mock_parse.return_value = (
            mock_response['data']['products'],
            'test_query',  # cluster = text
            hash('test_query'),  # preset = hash(text)
            mock_response['data']['total']
        )

        parser = ParserService()
        total_pages = TotalPages()
        result = await parser.parse_keywords_from_wb('test_query', 1, total_pages)

        assert len(result) == 1
        assert result[0].keyword_text == 'test_query'
        assert mock_parse.call_count == 1

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_search_catalog():
    """
    Тест проверяет парсинг при catalog_type != 'merger'
    В этом случае cluster берется из metadata['normquery']
    """
    mock_response = {
        'payloadVersion': 2,
        'metadata': {
            'catalog_type': 'search',
            'catalog_value': 'preset=12345',
            'normquery': 'normalized_query'
        },
        'data': {
            'total': 100,
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1,
                        'promoPosition': 1,
                        'tp': 'c'
                    }
                }
            ]
        }
    }

    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = (
            mock_response['data']['products'],
            mock_response['metadata']['normquery'],
            int(mock_response['metadata']['catalog_value'].split('=')[1]),
            mock_response['data']['total']
        )

        parser = ParserService()
        total_pages = TotalPages()
        result = await parser.parse_keywords_from_wb('test_query', 1, total_pages)

        # Проверяем что создаются две позиции: для исходного текста и для кластера
        assert len(result) == 2, "Должно быть создано 2 позиции: для исходного текста и для кластера"
        
        # Проверяем позицию для исходного текста
        assert result[0].keyword_text == 'test_query'
        assert result[0].nmid == 12345
        assert result[0].adv_id == 'test_adv_id'
        assert result[0].cpm == 100
        assert result[0].adv_type == 9  # тип рекламы - поиск
        
        # Проверяем позицию для кластера
        assert result[1].keyword_text == 'normalized_query'
        assert result[1].nmid == 12345
        assert result[1].adv_id == 'test_adv_id'
        assert result[1].cpm == 100
        assert result[1].adv_type is None  # для кластера тип рекламы не указывается
        
        assert mock_parse.call_count == 1

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_invalid_version():
    """
    Тест проверяет обработку неверной версии payload
    """
    mock_response = {
        'payloadVersion': 1,  # Неверная версия
        'metadata': {
            'catalog_type': 'merger',
            'normquery': 'test_query'
        },
        'data': {
            'total': 100,
            'products': []
        }
    }

    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        mock_parse.side_effect = DataError('Invalid payload version', 'test_query')

        parser = ParserService()
        total_pages = TotalPages()
        result = await parser.parse_keywords_from_wb('test_query', 1, total_pages)

        assert result == []  # Должен вернуться пустой список при ошибке
        assert mock_parse.call_count == 1

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_invalid_adv_type():
    """
    Тест проверяет обработку неизвестного типа рекламы
    Должно выбрасываться исключение DataError
    """
    mock_response = {
        'payloadVersion': 2,
        'metadata': {
            'catalog_type': 'merger',
            'normquery': 'test_query'
        },
        'data': {
            'total': 100,
            'products': [
                {
                    'id': 12345,
                    'log': {
                        'advertId': 'test_adv_id',
                        'cpm': 100,
                        'position': 1,
                        'promoPosition': 1,
                        'tp': 'x'  # Неизвестный тип рекламы
                    }
                }
            ]
        }
    }

    with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
        mock_parse.return_value = (
            mock_response['data']['products'],
            mock_response['metadata']['normquery'],
            hash('test_query'),
            mock_response['data']['total']
        )

        parser = ParserService()
        total_pages = TotalPages()
        
        # Проверяем что выбрасывается правильное исключение
        with pytest.raises(DataError) as exc_info:
            await parser.parse_keywords_from_wb('test_query', 1, total_pages)
        
        # Проверяем текст исключения
        assert str(exc_info.value) == "('Неизвестный тип рекламы x', 'test_query')"
        assert mock_parse.call_count == 1

@pytest.mark.asyncio
async def test_parse_keywords_from_wb_total_pages_calculation():
    """
    Тест проверяет корректность расчета общего количества страниц
    """
    test_cases = [
        (100, 2),   # 100 товаров = 2 страницы (100/100 + 1)
        (99, 1),    # 99 товаров = 1 страница
        (101, 2),   # 101 товар = 2 страницы
        (5999, 60), # 5999 товаров = 60 страниц (максимум)
        (6001, 60)  # Больше 6000 все равно даст 60 страниц
    ]

    for total_items, expected_pages in test_cases:
        mock_response = {
            'payloadVersion': 2,
            'metadata': {
                'catalog_type': 'merger',
                'normquery': 'test_query'
            },
            'data': {
                'total': total_items,
                'products': [{'id': 12345}]
            }
        }

        with patch.object(ParserService, '_ParserService__parse_keywords_from_wb', new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (
                mock_response['data']['products'],
                mock_response['metadata']['normquery'],
                hash('test_query'),
                mock_response['data']['total']
            )

            parser = ParserService()
            total_pages = TotalPages()
            await parser.parse_keywords_from_wb('test_query', 1, total_pages)

            assert total_pages.total_pages == expected_pages, f"Для {total_items} товаров ожидалось {expected_pages} страниц" 