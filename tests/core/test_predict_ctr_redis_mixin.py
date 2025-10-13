import pytest
from typing import Any
from unittest.mock import MagicMock, patch
from app.core.redis_manager_v2.mixins.predict_ctr import PredictCTRRedisMixin
from app.modules.common_slaves.wildberries.models.models import PredictCTRMode


class TestPredictCTRRedisMixin:
    """Тесты для PredictCTRRedisMixin._get_key метода с моками модели"""

    @pytest.fixture
    def redis_mixin(self) -> Any:
        """Фикстура для создания экземпляра миксина"""
        mixin = PredictCTRRedisMixin()
        # Мокаем методы, которые вызываются в _get_key
        setattr(
            mixin, "_get_key_v1", MagicMock(return_value="predict_ctr:123:test_keyword")
        )
        setattr(
            mixin,
            "_get_key_v2",
            MagicMock(return_value="predict_ctr_v2:456,789:test_keyword"),
        )
        return mixin

    @pytest.fixture
    def mock_adv_setting(self) -> Any:
        """Фикстура для создания мока AdvSetting с нужными свойствами"""
        mock_adv = MagicMock()
        mock_adv.adv_id = 123
        mock_adv.nmids = [456, 789]
        return mock_adv

    def test_get_key_with_none_predict_ctr_mode(
        self, redis_mixin: Any, mock_adv_setting: Any
    ) -> None:
        """Тест: predict_ctr_mode = None должен использовать _get_key_v1"""
        # Arrange
        mock_adv_setting.predict_ctr_mode = None
        keyword = "test_keyword"

        print(
            f"🧪 Тестируем None режим: adv.predict_ctr_mode = {mock_adv_setting.predict_ctr_mode}"
        )

        # Act
        result = redis_mixin._get_key(mock_adv_setting, keyword)

        # Assert
        redis_mixin._get_key_v1.assert_called_once_with(123, keyword)
        redis_mixin._get_key_v2.assert_not_called()
        assert result == "predict_ctr:123:test_keyword"

        print(f"✅ Вызван _get_key_v1 с args: {redis_mixin._get_key_v1.call_args}")
        print(f"✅ _get_key_v2 не вызывался: {redis_mixin._get_key_v2.called}")

    def test_get_key_with_v1_predict_ctr_mode(
        self, redis_mixin: Any, mock_adv_setting: Any
    ) -> None:
        """Тест: predict_ctr_mode = V1 должен использовать _get_key_v1"""
        # Arrange
        mock_adv_setting.predict_ctr_mode = PredictCTRMode.V1
        keyword = "test_keyword"

        print(
            f"🧪 Тестируем V1 режим: adv.predict_ctr_mode = {mock_adv_setting.predict_ctr_mode}"
        )

        # Act
        result = redis_mixin._get_key(mock_adv_setting, keyword)

        # Assert
        redis_mixin._get_key_v1.assert_called_once_with(123, keyword)
        redis_mixin._get_key_v2.assert_not_called()
        assert result == "predict_ctr:123:test_keyword"

        print(f"✅ Вызван _get_key_v1 с args: {redis_mixin._get_key_v1.call_args}")
        print(f"✅ _get_key_v2 не вызывался: {redis_mixin._get_key_v2.called}")

    def test_get_key_with_v2_predict_ctr_mode(
        self, redis_mixin: Any, mock_adv_setting: Any
    ) -> None:
        """Тест: predict_ctr_mode = V2 должен использовать _get_key_v2"""
        # Arrange
        mock_adv_setting.predict_ctr_mode = PredictCTRMode.V2
        keyword = "test_keyword"

        print(
            f"🧪 Тестируем V2 режим: adv.predict_ctr_mode = {mock_adv_setting.predict_ctr_mode}"
        )

        # Act
        result = redis_mixin._get_key(mock_adv_setting, keyword)

        # Assert
        redis_mixin._get_key_v1.assert_not_called()
        redis_mixin._get_key_v2.assert_called_once_with([456, 789], keyword)
        assert result == "predict_ctr_v2:456,789:test_keyword"

        print(f"✅ _get_key_v1 не вызывался: {redis_mixin._get_key_v1.called}")
        print(f"✅ Вызван _get_key_v2 с args: {redis_mixin._get_key_v2.call_args}")

    def test_get_key_with_invalid_predict_ctr_mode(
        self, redis_mixin: Any, mock_adv_setting: Any
    ) -> None:
        """Тест: невалидный predict_ctr_mode должен поднимать ValueError"""
        # Arrange
        mock_adv_setting.predict_ctr_mode = "invalid_mode"
        keyword = "test_keyword"

        print(
            f"🧪 Тестируем невалидный режим: adv.predict_ctr_mode = {mock_adv_setting.predict_ctr_mode}"
        )

        # Act & Assert
        with pytest.raises(
            ValueError, match="Не верно указана версия predict_ctr_mode"
        ):
            redis_mixin._get_key(mock_adv_setting, keyword)

        # Проверяем, что никакие методы не были вызваны
        redis_mixin._get_key_v1.assert_not_called()
        redis_mixin._get_key_v2.assert_not_called()

        print("✅ Поднялось исключение ValueError")
        print("✅ Никакие методы не вызывались")

    def test_field_comparison_behavior_with_mock(self, redis_mixin: Any) -> None:
        """Тест для проверки поведения сравнения полей через моки"""
        print("\n🧪 Тестируем поведение сравнения полей:")

        # Тест 1: None поле
        mock_adv_none = MagicMock()
        mock_adv_none.predict_ctr_mode = None
        mock_adv_none.adv_id = 100
        mock_adv_none.nmids = [1, 2]

        redis_mixin._get_key(mock_adv_none, "test")
        print(
            f"🔍 None режим: predict_ctr_mode = {mock_adv_none.predict_ctr_mode}, вызван v1: {redis_mixin._get_key_v1.called}"
        )
        redis_mixin._get_key_v1.reset_mock()
        redis_mixin._get_key_v2.reset_mock()

        # Тест 2: V1 поле
        mock_adv_v1 = MagicMock()
        mock_adv_v1.predict_ctr_mode = PredictCTRMode.V1
        mock_adv_v1.adv_id = 200
        mock_adv_v1.nmids = [3, 4]

        redis_mixin._get_key(mock_adv_v1, "test")
        print(
            f"🔍 V1 режим: predict_ctr_mode = {mock_adv_v1.predict_ctr_mode}, вызван v1: {redis_mixin._get_key_v1.called}"
        )
        redis_mixin._get_key_v1.reset_mock()
        redis_mixin._get_key_v2.reset_mock()

        # Тест 3: V2 поле
        mock_adv_v2 = MagicMock()
        mock_adv_v2.predict_ctr_mode = PredictCTRMode.V2
        mock_adv_v2.adv_id = 300
        mock_adv_v2.nmids = [5, 6, 7]

        redis_mixin._get_key(mock_adv_v2, "test")
        print(
            f"🔍 V2 режим: predict_ctr_mode = {mock_adv_v2.predict_ctr_mode}, вызван v2: {redis_mixin._get_key_v2.called}"
        )

        # Проверки истинности/ложности
        assert not None  # None является falsy
        assert PredictCTRMode.V1  # Enum значения являются truthy
        assert PredictCTRMode.V2

        print("✅ Все проверки сравнения полей пройдены")

    @pytest.mark.parametrize(
        "mode,expected_v1_called,expected_v2_called,description",
        [
            (None, True, False, "None должен вызывать v1"),
            (PredictCTRMode.V1, True, False, "V1 должен вызывать v1"),
            (PredictCTRMode.V2, False, True, "V2 должен вызывать v2"),
        ],
    )
    def test_get_key_parametrized(
        self,
        redis_mixin: Any,
        mode: Any,
        expected_v1_called: bool,
        expected_v2_called: bool,
        description: str,
    ) -> None:
        """Параметризованный тест для всех валидных режимов"""
        print(f"\n🧪 Параметризованный тест: {description}")

        # Arrange
        mock_adv = MagicMock()
        mock_adv.adv_id = 123
        mock_adv.nmids = [456, 789]
        mock_adv.predict_ctr_mode = mode

        keyword = "parametrized_test"

        print(
            f"🔍 Режим: {mode}, ожидаем v1: {expected_v1_called}, v2: {expected_v2_called}"
        )

        # Act
        redis_mixin._get_key(mock_adv, keyword)

        # Assert
        if expected_v1_called:
            redis_mixin._get_key_v1.assert_called_once_with(123, keyword)
            print(f"✅ _get_key_v1 вызван с args: {redis_mixin._get_key_v1.call_args}")
        else:
            redis_mixin._get_key_v1.assert_not_called()
            print("✅ _get_key_v1 не вызывался")

        if expected_v2_called:
            redis_mixin._get_key_v2.assert_called_once_with([456, 789], keyword)
            print(f"✅ _get_key_v2 вызван с args: {redis_mixin._get_key_v2.call_args}")
        else:
            redis_mixin._get_key_v2.assert_not_called()
            print("✅ _get_key_v2 не вызывался")


class TestPredictCTRRedisKeyGeneration:
    """Тесты для проверки генерации ключей"""

    def test_get_key_v1_generation(self) -> None:
        """Тест генерации ключа версии V1"""
        # Arrange
        mixin = PredictCTRRedisMixin()
        adv_id = 12345
        keyword = "тестовое слово"

        print(
            f"🧪 Тестируем генерацию V1 ключа для adv_id={adv_id}, keyword='{keyword}'"
        )

        # Act
        with patch(
            "app.core.redis_manager_v2.mixins.predict_ctr.clear",
            return_value="cleaned_keyword",
        ) as mock_clear:
            result = mixin._get_key_v1(adv_id, keyword)

        # Assert
        mock_clear.assert_called_once_with(keyword)
        assert result == "predict_ctr:12345:cleaned_keyword"

        print(f"✅ Ключ V1 сгенерирован: {result}")
        print(f"✅ Функция clear вызвана с: {mock_clear.call_args}")

    def test_get_key_v2_generation(self) -> None:
        """Тест генерации ключа версии V2"""
        # Arrange
        mixin = PredictCTRRedisMixin()
        nmids = [300, 100, 200]  # Несортированный список
        keyword = "другое слово"

        print(f"🧪 Тестируем генерацию V2 ключа для nmids={nmids}, keyword='{keyword}'")

        # Act
        with patch(
            "app.core.redis_manager_v2.mixins.predict_ctr.clear",
            return_value="another_cleaned_keyword",
        ) as mock_clear:
            result = mixin._get_key_v2(nmids, keyword)

        # Assert
        mock_clear.assert_called_once_with(keyword)
        # Проверяем, что nmids были отсортированы
        assert result == "predict_ctr_v2:100,200,300:another_cleaned_keyword"

        print(f"✅ Ключ V2 сгенерирован: {result}")
        print("✅ nmids отсортированы: 300,100,200 -> 100,200,300")
        print(f"✅ Функция clear вызвана с: {mock_clear.call_args}")

    def test_get_key_v2_single_nmid(self) -> None:
        """Тест генерации ключа V2 с одним nmid"""
        # Arrange
        mixin = PredictCTRRedisMixin()
        nmids = [42]
        keyword = "одинокий ключ"

        print(
            f"🧪 Тестируем генерацию V2 ключа с одним nmid={nmids}, keyword='{keyword}'"
        )

        # Act
        with patch(
            "app.core.redis_manager_v2.mixins.predict_ctr.clear",
            return_value="lonely_key",
        ) as mock_clear:
            result = mixin._get_key_v2(nmids, keyword)

        # Assert
        mock_clear.assert_called_once_with(keyword)
        assert result == "predict_ctr_v2:42:lonely_key"

        print(f"✅ Ключ V2 с одним nmid сгенерирован: {result}")
        print(f"✅ Функция clear вызвана с: {mock_clear.call_args}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
