from app import settings
from app.client_bot import const

is_first = True


# Функция для склонения слова "артикул"
def declension(number: int) -> str:
    if 10 <= number % 100 <= 20:  # Для чисел от 10 до 20 используем форму "артикулов"
        return "артикулов"
    elif number % 10 == 1:  # Для числа 1
        return "артикул"
    elif 2 <= number % 10 <= 4:  # Для чисел от 2 до 4
        return "артикула"
    else:  # Для остальных чисел
        return "артикулов"


text = f"""
Актуальный прайс  -> {const.PRICE_LINK}

Минимальная сумма пополнения: {settings.MIN_SUM} р.

"""
text = text.strip()
