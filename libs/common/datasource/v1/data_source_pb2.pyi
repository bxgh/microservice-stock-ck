from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class DataType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DATA_TYPE_UNSPECIFIED: _ClassVar[DataType]
    DATA_TYPE_QUOTES: _ClassVar[DataType]
    DATA_TYPE_TICK: _ClassVar[DataType]
    DATA_TYPE_HISTORY: _ClassVar[DataType]
    DATA_TYPE_RANKING: _ClassVar[DataType]
    DATA_TYPE_SECTOR: _ClassVar[DataType]
    DATA_TYPE_FINANCE: _ClassVar[DataType]
    DATA_TYPE_VALUATION: _ClassVar[DataType]
    DATA_TYPE_INDEX: _ClassVar[DataType]
    DATA_TYPE_INDUSTRY: _ClassVar[DataType]
    DATA_TYPE_META: _ClassVar[DataType]
    DATA_TYPE_ISSUE_PRICE: _ClassVar[DataType]
    DATA_TYPE_SW_INDUSTRY: _ClassVar[DataType]
    DATA_TYPE_FEATURES: _ClassVar[DataType]
    DATA_TYPE_THS_INDUSTRY: _ClassVar[DataType]
    DATA_TYPE_THS_CONCEPTS: _ClassVar[DataType]
    DATA_TYPE_FUTURES_KLINE_DAILY: _ClassVar[DataType]
    DATA_TYPE_MARGIN: _ClassVar[DataType]
DATA_TYPE_UNSPECIFIED: DataType
DATA_TYPE_QUOTES: DataType
DATA_TYPE_TICK: DataType
DATA_TYPE_HISTORY: DataType
DATA_TYPE_RANKING: DataType
DATA_TYPE_SECTOR: DataType
DATA_TYPE_FINANCE: DataType
DATA_TYPE_VALUATION: DataType
DATA_TYPE_INDEX: DataType
DATA_TYPE_INDUSTRY: DataType
DATA_TYPE_META: DataType
DATA_TYPE_ISSUE_PRICE: DataType
DATA_TYPE_SW_INDUSTRY: DataType
DATA_TYPE_FEATURES: DataType
DATA_TYPE_THS_INDUSTRY: DataType
DATA_TYPE_THS_CONCEPTS: DataType
DATA_TYPE_FUTURES_KLINE_DAILY: DataType
DATA_TYPE_MARGIN: DataType

class DataRequest(_message.Message):
    __slots__ = ("type", "codes", "params", "request_id")
    class ParamsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TYPE_FIELD_NUMBER: _ClassVar[int]
    CODES_FIELD_NUMBER: _ClassVar[int]
    PARAMS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    type: DataType
    codes: _containers.RepeatedScalarFieldContainer[str]
    params: _containers.ScalarMap[str, str]
    request_id: str
    def __init__(self, type: _Optional[_Union[DataType, str]] = ..., codes: _Optional[_Iterable[str]] = ..., params: _Optional[_Mapping[str, str]] = ..., request_id: _Optional[str] = ...) -> None: ...

class DataResponse(_message.Message):
    __slots__ = ("success", "error_message", "binary_data", "json_data", "source_name", "latency_ms", "format")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    BINARY_DATA_FIELD_NUMBER: _ClassVar[int]
    JSON_DATA_FIELD_NUMBER: _ClassVar[int]
    SOURCE_NAME_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error_message: str
    binary_data: bytes
    json_data: str
    source_name: str
    latency_ms: int
    format: str
    def __init__(self, success: bool = ..., error_message: _Optional[str] = ..., binary_data: _Optional[bytes] = ..., json_data: _Optional[str] = ..., source_name: _Optional[str] = ..., latency_ms: _Optional[int] = ..., format: _Optional[str] = ...) -> None: ...

class Capabilities(_message.Message):
    __slots__ = ("supported_types", "priority", "version")
    SUPPORTED_TYPES_FIELD_NUMBER: _ClassVar[int]
    PRIORITY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    supported_types: _containers.RepeatedScalarFieldContainer[DataType]
    priority: int
    version: str
    def __init__(self, supported_types: _Optional[_Iterable[_Union[DataType, str]]] = ..., priority: _Optional[int] = ..., version: _Optional[str] = ...) -> None: ...

class Empty(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthStatus(_message.Message):
    __slots__ = ("healthy", "message")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    message: str
    def __init__(self, healthy: bool = ..., message: _Optional[str] = ...) -> None: ...
