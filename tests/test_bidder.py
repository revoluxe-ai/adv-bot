import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from tests.mocks import MockAdvSetting, MockWBCabinet, MockKeywordSetting, MockUser, MockWBUserCabinet

# Заглушка для биддера - функции будут реализованы аналогично pricer.py
def calculate_optimal_bid(current_bid, min_bid, search_count, ctr):
    """
    Расчет оптимальной ставки для ключевого слова
    
    Args:
        current_bid (float): текущая ставка
        min_bid (float): минимальная ставка
        search_count (int): количество поисков
        ctr (float): прогнозируемый CTR
        
    Returns:
        float: оптимальная ставка
    """
    # Если CTR слишком низкий, не рекомендуем делать высокую ставку
    if ctr < 0.001:
        return min_bid
    
    # Учитываем количество поисков при расчете
    if search_count < 50:
        bid_multiplier = 1.0
    elif search_count < 200:
        bid_multiplier = 1.2
    elif search_count < 1000:
        bid_multiplier = 1.5
    else:
        bid_multiplier = 2.0
    
    # Рассчитываем оптимальную ставку
    optimal_bid = min_bid * (1 + ctr * 10) * bid_multiplier
    
    # Не делаем ставку слишком низкой или слишком высокой
    return max(min_bid, min(current_bid * 1.5, optimal_bid))

def estimate_traffic(bid, min_bid, search_count, ctr, competition_level):
    """
    Оценка трафика для заданной ставки
    
    Args:
        bid (float): ставка
        min_bid (float): минимальная ставка
        search_count (int): количество поисков
        ctr (float): CTR ключевого слова
        competition_level (float): уровень конкуренции (от 0 до 1)
        
    Returns:
        int: прогнозируемое количество кликов
    """
    if bid < min_bid:
        return 0
    
    # Коэффициент снижения в зависимости от конкуренции
    competition_factor = 1 - competition_level * 0.7
    
    # Базовая оценка трафика
    base_traffic = search_count * ctr
    
    # Коэффициент в зависимости от соотношения ставки к минимальной
    bid_factor = min(2.0, bid / min_bid)
    
    # Учитываем все факторы
    estimated_traffic = base_traffic * bid_factor * competition_factor
    
    return int(estimated_traffic)

def calculate_roi(bid, min_bid, search_count, ctr, conversion_rate, average_order_value, cost_per_item):
    """
    Расчет ROI для заданной ставки
    
    Args:
        bid (float): ставка
        min_bid (float): минимальная ставка
        search_count (int): количество поисков
        ctr (float): CTR ключевого слова
        conversion_rate (float): конверсия в заказ
        average_order_value (float): средний чек
        cost_per_item (float): себестоимость товара
        
    Returns:
        float: прогнозируемый ROI в процентах
    """
    if bid < min_bid:
        return 0
    
    # Оценка количества кликов
    clicks = estimate_traffic(bid, min_bid, search_count, ctr, 0.5)
    
    # Расчет количества заказов
    orders = clicks * conversion_rate
    
    # Расчет расходов на рекламу
    ad_spend = clicks * bid
    
    # Расчет дохода
    revenue = orders * average_order_value
    
    # Расчет себестоимости
    cost = orders * cost_per_item
    
    # Расчет прибыли
    profit = revenue - cost - ad_spend
    
    # Расчет ROI
    if ad_spend == 0:
        return 0
    
    roi = (profit / ad_spend) * 100
    
    return roi

class TestBidder:
    
    def test_calculate_optimal_bid(self):
        # Тестовые данные
        current_bid = 100.0
        min_bid = 50.0
        search_count = 500
        ctr = 0.05
        
        # Вызываем функцию
        result = calculate_optimal_bid(current_bid, min_bid, search_count, ctr)
        
        # Проверяем результат
        assert isinstance(result, float)
        assert result >= min_bid
        # Проверяем, что при высоком CTR и search_count ставка будет увеличена
        assert result > current_bid
    
    def test_calculate_optimal_bid_low_ctr(self):
        # Тестовые данные с низким CTR
        current_bid = 100.0
        min_bid = 50.0
        search_count = 500
        ctr = 0.0005  # очень низкий CTR
        
        # Вызываем функцию
        result = calculate_optimal_bid(current_bid, min_bid, search_count, ctr)
        
        # Проверяем результат
        assert result == min_bid  # для очень низкого CTR должна быть минимальная ставка
    
    def test_estimate_traffic(self):
        # Тестовые данные
        bid = 100.0
        min_bid = 50.0
        search_count = 1000
        ctr = 0.05
        competition_level = 0.5
        
        # Вызываем функцию
        result = estimate_traffic(bid, min_bid, search_count, ctr, competition_level)
        
        # Проверяем результат
        assert isinstance(result, int)
        assert result >= 0
        # Проверяем примерное значение
        expected_traffic = int(1000 * 0.05 * (100/50) * (1 - 0.5 * 0.7))
        assert result == expected_traffic
    
    def test_calculate_roi(self):
        # Тестовые данные
        bid = 100.0
        min_bid = 50.0
        search_count = 1000
        ctr = 0.05
        conversion_rate = 0.1
        average_order_value = 2000.0
        cost_per_item = 1000.0
        
        # Вызываем функцию
        result = calculate_roi(bid, min_bid, search_count, ctr, conversion_rate, average_order_value, cost_per_item)
        
        # Проверяем результат
        assert isinstance(result, float)
        # Проверка логики: при заданных условиях ROI должен быть положительным
        assert result > 0
    
    def test_calculate_roi_unprofitable(self):
        # Тестовые данные для убыточной кампании
        bid = 300.0  # очень высокая ставка
        min_bid = 50.0
        search_count = 100  # мало поисков
        ctr = 0.01  # низкий CTR
        conversion_rate = 0.05  # низкая конверсия
        average_order_value = 1500.0
        cost_per_item = 1000.0
        
        # Вызываем функцию
        result = calculate_roi(bid, min_bid, search_count, ctr, conversion_rate, average_order_value, cost_per_item)
        
        # Проверяем результат - должен быть отрицательным или около нуля
        assert result <= 30 