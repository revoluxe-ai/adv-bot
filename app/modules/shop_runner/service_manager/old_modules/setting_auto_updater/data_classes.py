from pydantic import BaseModel, ConfigDict, field_validator

from app.modules.common_slaves.wildberries.models.fact_methods_enum import FactMethods


class FactData(BaseModel):
    predict_orders: float
    original_orders: float
    pay_for_order: float
    fact_method: FactMethods
    # Настройки для автоматического преобразования типов
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        use_enum_values=True,  # Enum -> value
        ser_json_timedelta="iso8601",  # если где-то timedelta
        ser_json_bytes="base64",  # на будущее
    )

    @property
    def method_ru(self) -> str:
        # TODO: Сделать тест сюда - упало в проде
        if FactMethods(self.fact_method) == FactMethods.DIRECT_SALES:
            return "По прямым продажам"
        elif FactMethods(self.fact_method) == FactMethods.BY_CARTS:
            return "По корзинам"
        else:
            raise NotImplementedError(
                f"Неизвестный метод расчета факта: {self.fact_method}"
            )


class PlanData(BaseModel):
    orders: int
    target_pay_for_order: int
    max_pay_for_order: int

    # Валидатор для полей типа int (преобразует float -> int, если значение целое)
    @field_validator("*")
    @classmethod
    def validate_ints(cls, value):
        if isinstance(value, float):
            if not value.is_integer():
                raise ValueError("Дробное значение недопустимо")
            return int(value)
        return value

    @property
    def full_settings(self) -> bool:
        return all(
            [
                self.orders is not None,
                self.target_pay_for_order is not None,
                self.max_pay_for_order is not None,
            ]
        )

    model_config = ConfigDict(
        use_enum_values=True,  # Enum -> value
        ser_json_timedelta="iso8601",  # если где-то timedelta
        ser_json_bytes="base64",  # на будущее
    )
