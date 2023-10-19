from __future__ import annotations

from typing import Any


class Response:
    __slots__: tuple[str, ...] = (
        '__status',
        '__value',
    )
    rtype: str = 'system'

    def __init__(self, status: str, value: Any) -> None:
        self.__status: str = status
        if type(value) is str:
            self.__value = iter([value])
        elif type(value) is list:
            self.__value = iter(value)
        else:
            self.__value = value

    @property
    def status(self) -> str:
        return self.__status

    @property
    def is_ok(self) -> bool:
        return True if self.__status == 'success' else False

    @property
    def value(self) -> Any:
        return self.__value

    @classmethod
    def error(cls, value: Any) -> Response:
        return cls('error', value)

    @classmethod
    def success(cls, value: Any = '') -> Response:
        return cls('success', value)

class SettingsResponse(Response):
    ...

class AlertResponse(Response):
    ...

class ContextResponse(Response):
    rtype: str = 'data'

class RichResponse(Response):
    rtype: str = 'rich'
