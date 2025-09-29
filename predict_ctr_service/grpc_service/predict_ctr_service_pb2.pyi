from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PredictCtrRequest(_message.Message):
    __slots__ = ("nmids", "phrases")
    NMIDS_FIELD_NUMBER: _ClassVar[int]
    PHRASES_FIELD_NUMBER: _ClassVar[int]
    nmids: _containers.RepeatedScalarFieldContainer[int]
    phrases: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        nmids: _Optional[_Iterable[int]] = ...,
        phrases: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class PredictCtrResponse(_message.Message):
    __slots__ = ("predictions",)

    class PredictionsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[float] = ...
        ) -> None: ...

    PREDICTIONS_FIELD_NUMBER: _ClassVar[int]
    predictions: _containers.ScalarMap[str, float]
    def __init__(self, predictions: _Optional[_Mapping[str, float]] = ...) -> None: ...
