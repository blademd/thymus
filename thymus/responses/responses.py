from __future__ import annotations

from typing import TYPE_CHECKING

import sys


if TYPE_CHECKING:
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Iterable
    else:
        from typing import Iterable


class Response:
    __slots__: tuple[str, ...] = (
        '__status',
        '__value',
    )
    rtype: str = 'system'

    def __init__(self, status: str, value: str | Iterable[str]) -> None:
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
    def value(self) -> Iterable[str]:
        return self.__value

    @classmethod
    def error(cls, value: str | Iterable[str]) -> Response:
        return cls('error', value)

    @classmethod
    def success(cls, value: str | Iterable[str] = '') -> Response:
        return cls('success', value)

class SettingsResponse(Response):
    ...

class AlertResponse(Response):
    ...

class ContextResponse(Response):
    rtype: str = 'data'
