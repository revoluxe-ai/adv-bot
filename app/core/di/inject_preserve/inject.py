"""Типобезопасная обёртка вокруг dependency_injector.wiring.inject / Provide.

Цель: не ломать аннотации (mypy) при использовании Provide[...] как значения по умолчанию.

Подход:
- inject: возвращает ту же функцию, но через dependency_injector, с корректным generic cast.
- Provide: тонкий типовой прокси. В момент индексирования возвращает реальный Provide из библиотеки,
  поэтому runtime-совместимость сохраняется. Для type checker наш класс имеет Generic[T],
  что не конфликтует с аннотированным целевым типом параметра.

Использование:
    from app.core.di import inject, Provide, AppContainer

    @inject
    def f(service: Service = Provide[AppContainer.some_service]): ...

Mypy увидит параметр как Service (а не union c Provide), потому что значение по умолчанию — Any.
"""

from __future__ import annotations

from typing import Any, Callable, TypeVar, cast, Generic

from dependency_injector.wiring import inject as _inject

F = TypeVar("F", bound=Callable[..., Any])


def inject(func: F) -> F | Callable[[F], F]:
    """Обёртка над dependency_injector.wiring.inject c сохранением типа исходной функции."""
    if func is None:
        def _decorator(real_func: F) -> F:
            return cast(F, _inject(real_func))

        return _decorator
    return _inject(func)


# Типовой прокси. Идея: Provide[T] -> возвращаем реальный Provide из dependency_injector,
# но type-checker видит здесь Generic[T], не меняя тип параметра функции.
class Provide(Generic[F]):  # noqa: D401
    def __class_getitem__(cls, item: Any) -> Any:  # noqa: D401
        from dependency_injector.wiring import Provide as _RealProvide  # локальный импорт
        return _RealProvide[item]


__all__ = ["inject", "Provide"]
