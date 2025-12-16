import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def get_price_for_day_for_shop(shop_id, day):
    """
    Получение цены за день для магазина

    Args:
        shop_id (str): ID магазина
        day (date): день для расчета

    Returns:
        float: цена за день
    """
    logger.info(f"Получение цены за день {day} для магазина {shop_id}")
    # Мок функции, возвращает фиксированное значение
    return 0.001


def predict_keyword_ctr(keyword, nmid):
    """
    Прогнозирование CTR для ключевого слова и товара

    Args:
        keyword (str): ключевое слово
        nmid (int): ID товара

    Returns:
        float: прогнозируемый CTR
    """
    logger.info(f"Прогнозирование CTR для ключевого слова {keyword} и товара {nmid}")
    # Мок функции, возвращает случайное значение в диапазоне 0-1
    return np.random.random() * 0.1


def get_minimal_bet(keyword, adv_id):
    """
    Получение минимальной ставки для ключевого слова в рекламной кампании

    Args:
        keyword (str): ключевое слово
        adv_id (str): ID рекламной кампании

    Returns:
        float: минимальная ставка
    """
    logger.info(
        f"Получение минимальной ставки для ключевого слова {keyword} в рекламной кампании {adv_id}"
    )
    # Мок функции, возвращает случайное значение от 50 до 150
    return np.random.randint(50, 150)


def get_adv_costs(adv_setting, start_date, end_date):
    """
    Получение затрат на рекламу для заданного периода

    Args:
        adv_setting (AdvSetting): настройки рекламной кампании
        start_date (date): начальная дата периода
        end_date (date): конечная дата периода

    Returns:
        pd.DataFrame: DataFrame с затратами по дням
    """
    logger.info(
        f"Получение затрат на рекламу для кампании {adv_setting.adv_id} с {start_date} по {end_date}"
    )

    # Создаем диапазон дат
    date_range = pd.date_range(start=start_date, end=end_date)

    # Создаем данные для каждого дня
    data = []
    for date in date_range:
        day_date = date.date()
        # Для каждого дня рассчитываем сумму затрат
        day_sum = sum(
            [
                keyword.cpm_bid * np.random.randint(5, 20) / 100
                for keyword in adv_setting.keyword_settings
            ]
        )
        data.append({"date": day_date, "sum": day_sum})

    # Создаем DataFrame
    df = pd.DataFrame(data)
    return df


def get_position_from_bet(bet, min_bet, bets):
    """
    Получение позиции по ставке

    Args:
        bet (float): текущая ставка
        min_bet (float): минимальная ставка
        bets (list): список всех ставок

    Returns:
        int: позиция (0-based index)
    """
    logger.info(f"Получение позиции для ставки {bet} (мин. ставка: {min_bet})")

    # Если ставка меньше минимальной, товар не показывается
    if bet < min_bet:
        return -1

    # Сортируем ставки по убыванию
    sorted_bets = sorted(bets, reverse=True)

    # Ищем позицию для нашей ставки
    for i, other_bet in enumerate(sorted_bets):
        if bet >= other_bet:
            return i

    # Если наша ставка меньше всех, возвращаем последнюю позицию
    return len(sorted_bets)
