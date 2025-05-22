from pydantic import BaseModel, field_validator, ConfigDict


class FactData(BaseModel):
    predict_orders: float
    original_orders: int
    pay_for_order: float

    # Настройки для автоматического преобразования типов
    model_config = ConfigDict(arbitrary_types_allowed=True)


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
