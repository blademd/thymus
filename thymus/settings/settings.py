from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Type, Optional, Any


class Setting(ABC):
    __slots__ = (
        '_var_type',
        '_fixed_values',
        '_description',
        '_show',
        '_read_only',
        '_pass_through',
    )

    def __init__(
        self,
        var_type: Type[str | int | bool],
        *,
        description: str,
        fixed_values: Optional[tuple] = None,
        show=True,
        read_only=False,
        pass_through=False,
    ) -> None:
        self._var_type = var_type
        self._description = description
        self._fixed_values: Optional[tuple] = None
        self._show = show
        self._read_only = read_only
        self._pass_through = pass_through
        self._fixed_setter(fixed_values)

    def __repr__(self) -> str:
        r = f'Type: {self._var_type}. Value: {self.value}. Visible: {self._show}.'
        return r

    @property
    @abstractmethod
    def value(self) -> Any:
        raise NotImplementedError

    @value.setter
    @abstractmethod
    def value(self, v: Any) -> None:
        raise NotImplementedError

    @property
    def description(self) -> str:
        return self._description

    @description.setter
    def description(self, v: str) -> None:
        if not isinstance(v, str):
            raise TypeError('Description must be str.')
        self._description = v

    @property
    def show(self) -> bool:
        return self._show

    @property
    def read_only(self) -> bool:
        return self._read_only

    @property
    def pass_through(self) -> bool:
        return self._pass_through

    @property
    def fixed_values(self) -> Optional[tuple]:
        return self._fixed_values

    def _fixed_setter(self, v: Optional[tuple]) -> None:
        if v is None:
            self._fixed_values = None
            return

        if not isinstance(v, tuple):
            raise TypeError('Fixed values type is not tuple.')

        if len(set(v)) != len(v):
            raise ValueError('There are duplicates in the fixed list.')

        for x in v:
            if not isinstance(x, self._var_type):
                raise TypeError(f'One of the fixed list is not {self._var_type}.')

        self._fixed_values = v


class IntSetting(Setting):
    __slots__ = (
        '_value',
        '_range',
        '_negative',
        '_non_zero',
    )

    def __init__(
        self,
        value: int,
        *,
        description='',
        val_range: Optional[tuple[int, int]] = None,
        fixed_values: Optional[tuple[int, ...]] = None,
        negative=True,
        non_zero=False,
        show=True,
        read_only=False,
        pass_through=False,
    ) -> None:
        super().__init__(
            int,
            description=description,
            fixed_values=fixed_values,
            show=show,
            read_only=read_only,
            pass_through=pass_through,
        )
        self._value = 0
        self._range: Optional[tuple[int, int]] = None
        self._negative = negative
        self._non_zero = non_zero
        self._range_setter(val_range)
        self.value = value

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, v: int) -> None:
        if not isinstance(v, int):
            raise TypeError('Value type must be int.')

        if not self._negative and v < 0:
            raise ValueError('Cannot be negative.')

        if self._non_zero and not v:
            raise ValueError('Cannot be zero.')

        if self._range:
            min, max = self._range
            if min > v:
                raise ValueError(f'Value is too small (< {min}).')
            elif max < v:
                raise ValueError(f'Value is too big (> {max}).')

        elif self._fixed_values:
            if v not in self._fixed_values:
                raise ValueError('Value is not in the fixed list.')

        self._value = v

    def _range_setter(self, v: Optional[tuple[int, int]]) -> None:
        if v is None:
            self._range = None
            return

        if not isinstance(v, tuple):
            raise TypeError('Range type is not tuple.')

        if len(v) != 2:
            raise ValueError('Too many elements for the range. Must be two.')

        for x in v:
            if not isinstance(x, int):
                raise TypeError('One of the range elements is not int.')
            elif x < 0:
                raise ValueError('One of the range elements is negative.')

        min, max = v

        if min > max:
            raise ValueError('Min is greater than max in the range.')

        self._range = v


class StrSetting(Setting):
    __slots__ = (
        '_value',
        '_max_length',
        '_encoding',
        '_empty',
    )

    def __init__(
        self,
        value: str,
        *,
        description='',
        fixed_values: Optional[tuple[str, ...]] = None,
        max_length=1000,
        encoding=False,
        empty=True,
        show=True,
        read_only=False,
        pass_through=False,
    ) -> None:
        super().__init__(
            str,
            description=description,
            fixed_values=fixed_values,
            show=show,
            read_only=read_only,
            pass_through=pass_through,
        )
        self._value = ''
        if max_length < 0:
            raise ValueError('Length cannot be negative.')
        self._max_length = max_length
        self._encoding = encoding
        self._empty = empty
        self.value = value

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, v: str) -> None:
        if not isinstance(v, str):
            raise TypeError('Value type must be str.')

        if not self._empty and not v:
            raise ValueError('Value cannot be an empty string.')

        if self._encoding:
            try:
                'SCHLOP'.encode(v)
            except LookupError:
                raise ValueError(f'Incorrect encoding: {v}.')

        if self._max_length:
            if len(v) > self._max_length:
                raise ValueError(f'Value is longer than {self._max_length}.')

        if self._fixed_values:
            if v not in self._fixed_values:
                raise ValueError('Value is not in the fixed list.')

        self._value = v

    @property
    def max_length(self) -> int:
        return self._max_length


class BoolSetting(Setting):
    __slots__ = ('_value',)

    def __init__(self, value: bool, *, description='', show=True, read_only=False, pass_through=False) -> None:
        super().__init__(bool, description=description, show=show, read_only=read_only, pass_through=pass_through)
        self._value = False
        self.value = value

    @property
    def value(self) -> bool:
        return self._value

    @value.setter
    def value(self, v: bool) -> None:
        if isinstance(v, bool):
            self._value = v
        else:
            raise TypeError('Incorrect type for bool.')
