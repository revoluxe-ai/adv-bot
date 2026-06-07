"""Совместимый вход для исходных stand-тестов bid-math модели.

Математика, синтетика и regression-тесты находятся в ``tests.bid_math``.
Импорты сохраняют возможность запускать прежний путь тестового файла.
"""

from tests.bid_math.test_bid_model_regression import (
    test_one_strong_night_hour_can_become_top_expected_and_test_candidate,
    test_sparse_confirmed_bid_becomes_best_main_candidate,
)

__all__ = [
    "test_one_strong_night_hour_can_become_top_expected_and_test_candidate",
    "test_sparse_confirmed_bid_becomes_best_main_candidate",
]
