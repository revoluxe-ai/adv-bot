def get_pause(max_iterations_per_minute: int) -> float:  # Максимальное количество итераций в секунду
    pause = 1 * 60 / max_iterations_per_minute  # Пауза в секундах
    return pause
