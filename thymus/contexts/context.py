from __future__ import annotations

from functools import reduce
from collections import deque
from typing import TYPE_CHECKING
from logging import Logger, getLogger

from ..responses import AlertResponse
from ..lexers import CommonLexer

import shlex
import re
import sys
import os


if TYPE_CHECKING:
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Generator, Iterable
    else:
        from typing import Generator, Iterable

    from ..responses import Response

UP_LIMIT = 8


class Context:
    __slots__: tuple[str, ...] = (
        '__name',
        '__content',
        '__encoding',
        '__spaces',
        '__logger',
    )
    __names_cache: list[tuple[Context, str]] = []
    delimiter: str = '^'
    keywords: dict[str, list[str]] = {
        'go': ['go'],
        'show': ['show'],
        'top': ['top'],
        'up': ['up'],
        'filter': ['filter'],
        'wildcard': ['wildcard'],
        'stubs': ['stubs'],
        'sections': ['sections'],
        'version': ['version', 'ver'],
        'save': ['save'],
        'count': ['count'],
        'diff': ['diff'],
        'set': ['set'],
    }
    lexer: CommonLexer = CommonLexer

    @property
    def prompt(self) -> str:
        return ''

    @property
    def name(self) -> str:
        return self.__name

    @property
    def encoding(self) -> str:
        return self.__encoding

    @property
    def content(self) -> list[str]:
        return self.__content

    @property
    def spaces(self) -> int:
        return self.__spaces

    @property
    def nos_type(self) -> str:
        return ''

    @property
    def logger(self) -> Logger:
        return self.__logger

    @spaces.setter
    def spaces(self, value: int | str) -> None:
        if type(value) is str and value.isdigit():
            value = int(value)
        if value not in (1, 2, 4):
            raise ValueError('Spaces number can be 1, 2, 4.')
        self.__spaces = value

    @name.setter
    def name(self, value: str) -> None:
        if type(value) is not str or not re.match(r'^[0-9a-z]{4,16}$', value, re.I):
            raise ValueError('Incorrect format of the name: use only these 0-9 or a-z.\nFrom 4 to 16 symbols.')
        if (type(self), value) not in self.__names_cache:
            self.__names_cache.append((type(self), value))
        else:
            raise ValueError(f'The name "{value}" is already set.')
        self.__name = value

    @encoding.setter
    def encoding(self, value: str) -> None:
        try:
            'schlop'.encode(value)
            self.__encoding = value
        except LookupError:
            raise ValueError(f'"{value}" is not a correct encoding.')

    @logger.setter
    def logger(self, value: Logger) -> None:
        if type(value) is not Logger:
            raise ValueError('Incorrect type of a logger.')
        self.__logger = value

    def __init__(
        self,
        name: str,
        content: list[str],
        *,
        encoding: str,
        settings: dict[str, str | int],
        logger: Logger
    ) -> None:
        self.__name = name
        self.__content = content
        self.__encoding = encoding
        self.__logger = logger if logger else getLogger()
        self.__spaces = 2
        self.apply_settings(settings)

    def free(self) -> None:
        if (type(self), self.__name) in self.__names_cache:
            self.__names_cache.remove((type(self), self.__name))

    def apply_settings(self, settings: dict[str, str | int]) -> None:
        for k, v in settings.items():
            try:
                if type(v) is not str and type(v) is not int:
                    raise TypeError(f'A value for the key "{k}" has a wrong type: {type(v)}.')
                setattr(self, k, v)
            except Exception as err:
                self.__logger.error(f'{err}')

    def command_show(self, args: deque[str] = [], mods: list[list[str]] = []) -> Response:
        raise NotImplementedError

    def command_go(self, args: deque[str]) -> Response:
        raise NotImplementedError

    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
        raise NotImplementedError

    def command_up(self, args: deque[str]) -> Response:
        raise NotImplementedError

    def command_set(self, args: deque[str]) -> Response:
        if not args:
            return AlertResponse.error('Not enough arguments for "set".')
        command = args.popleft()
        command = command.lower()
        if len(args) != 1:
            return AlertResponse('error', f'There must be one argument for "set {command}".')
        value = args.popleft()
        value = value.lower()
        try:
            setattr(self, command, value)
        except (TypeError, ValueError) as err:
            return AlertResponse.error(f'{err}')
        except AttributeError:
            return AlertResponse.error(f'Unknown argument for "set": {command}.')
        return AlertResponse.success(f'The "set {command}" was successfully modified.')

    def mod_filter(self, data: Iterable[str], args: list[str]) -> Generator[str | FabricException, None, None]:
        if not data or len(args) != 1:
            yield FabricException('Incorrect arguments for "filter".')
        try:
            regexp = re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "filter": {args[0]}.')
        else:
            try:
                head = next(data)
                if isinstance(head, Exception):
                    yield head
                else:
                    yield '\n'
                    for line in filter(lambda x: regexp.search(x), data):
                        yield line.strip()
            except StopIteration:
                yield FabricException

    def mod_save(self, data: Iterable[str], args: list[str]) -> Generator[str | FabricException, None, None]:
        # terminating modificator
        if len(args) == 1 and data:
            destination = args[0]
            try:
                head = next(data)
                if isinstance(head, Exception):
                    yield head
                else:
                    with open(destination, 'w', encoding=self.encoding) as f:
                        for line in data:
                            f.write(f'{line}\n')
                        f.flush()
                        os.fsync(f.fileno())
                        yield '\n'
                        yield f'File "{destination}" was successfully saved.'
            except FileNotFoundError:
                yield FabricException(f'No such file or directory for "save": {destination}.')
            except StopIteration:
                yield FabricException
        else:
            yield FabricException('Incorrect arguments for "save".')

    def mod_count(self, data: Iterable[str], args: list[str]) -> Generator[str | FabricException, None, None]:
        # terminating modificator
        if args:
            raise FabricException('Incorrect arguments for "count".')
        try:
            head = next(data)
            if isinstance(head, Exception):
                yield head
            else:
                counter = 0
                for _ in filter(lambda x: x, data):
                    counter += 1
                yield '\n'
                yield f'Count: {counter}.'
        except StopIteration:
            yield FabricException

    def on_enter(self, value: str) -> Response:
        try:
            args = reduce(
                lambda acc, x: acc[:-1] + [acc[-1] + [x]] if x != '|' else acc + [[]],
                shlex.split(value),
                [[]]
            )
            head = deque(args[0])  # the line before a possible pipe symbol
            command = head.popleft()
            if command in self.keywords['show']:
                return self.command_show(head, args[1:])
            elif command in self.keywords['go']:
                return self.command_go(head)
            elif command in self.keywords['top']:
                return self.command_top(head, args[1:])
            elif command in self.keywords['up']:
                return self.command_up(head)
            elif command in self.keywords['set']:
                return self.command_set(head)
            else:
                return AlertResponse.error(f'Unknown command "{command}".')
        except IndexError:
            return AlertResponse.error('')
        except ValueError as err:
            return AlertResponse.error(f'Enter strike returns: {err}.')
        except NotImplementedError:
            return AlertResponse.error(f'The method for "{command}" is not implemented yet.')

    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        raise NotImplementedError

    def get_virtual_from(self, value: str) -> str:
        raise NotImplementedError

class FabricException(Exception):
    pass
