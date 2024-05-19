from __future__ import annotations

from typing import Any, Literal, Optional


class Response:
    __slots__ = (
        'status',
        'value',
        'mode',
    )

    @classmethod
    def error(cls, value: Any) -> Response:
        return cls('error', value)

    @classmethod
    def success(cls, value: Optional[Any] = None) -> Response:
        return cls('success', value)

    def __init__(
        self, status: Literal['error', 'success'], value: Any, mode: Literal['data', 'rich', 'system'] = 'data'
    ) -> None:
        self.status: Literal['error', 'success'] = status
        if type(value) is str:
            self.value = iter([value])
        elif type(value) is list:
            self.value = iter(value)
        else:
            self.value = value
        self.mode: Literal['data', 'rich', 'system'] = mode


class SystemResponse(Response):
    def __init__(self, status: Literal['error', 'success'], value: Any) -> None:
        super().__init__(status, value, 'system')
