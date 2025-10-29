from typing import Any


class TypedClass:
    def __init__(self, **kwargs: Any) -> None:
        annotations = self.__annotations__
        for name, value in kwargs.items():
            if name not in annotations:
                raise TypeError(f"Unexpected argument: {name}")
            if not isinstance(value, annotations[name]):
                raise TypeError(
                    f"Invalid type for {name}: expected {annotations[name]}, got {type(value)}"
                )
            setattr(self, name, value)
