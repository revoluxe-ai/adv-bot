def get_day_suffix(number: int) -> str:
    if 11 <= number % 100 <= 14:
        return f"{number} дней"
    elif number % 10 == 1:
        return f"{number} день"
    elif 2 <= number % 10 <= 4:
        return f"{number} дня"
    else:
        return f"{number} дней"
