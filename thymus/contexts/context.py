from __future__ import annotations

import shlex
import re
import sys
import os

from functools import reduce
from collections import deque
from typing import Any
from logging import Logger, getLogger
from abc import ABC, abstractmethod

from .. import SAVES_DIR
from ..responses import Response, AlertResponse
from ..lexers import CommonLexer

if sys.version_info.major == 3 and sys.version_info.minor >= 9:
    from collections.abc import Generator, Iterator
else:
    from typing import Generator, Iterator


UP_LIMIT = 8
CMD_LOG_LIMIT = 30


class Context(ABC):
    __slots__: tuple[str, ...] = (
        '__name',
        '__content',
        '__encoding',
        '__spaces',
        '__logger',
        '__commands_log',
        '__commands_index',
    )
    __names_cache: list[tuple[type[Context], str]] = []
    delimiter: str = '^'
    keywords: dict[str, list[str]] = {
        'go': ['go'],
        'show': ['show'],
        'top': ['top'],
        'up': ['up'],
        'filter': ['filter', 'grep'],
        'wildcard': ['wildcard'],
        'stubs': ['stubs'],
        'sections': ['sections'],
        'version': ['version', 'ver'],
        'save': ['save'],
        'count': ['count'],
        'diff': ['diff'],
        'set': ['set'],
        'contains': ['contains'],
        'help': ['help'],
        'global': ['global'],
    }
    lexer: type[CommonLexer] = CommonLexer

    @property
    @abstractmethod
    def prompt(self) -> str:
        raise NotImplementedError

    @property
    def name(self) -> str:
        return self.__name

    @name.setter
    def name(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Context name type must str.')
        if not re.match(r'^[0-9a-z]{4,16}$', value, re.I):
            raise ValueError('Incorrect format of the name: use only these 0-9 or a-z.\nFrom 4 to 16 symbols.')
        if (type(self), value) not in self.__names_cache:
            self.__names_cache.append((type(self), value))
        else:
            raise ValueError(f'The name "{value}" is already set.')
        self.__name = value

    @property
    def encoding(self) -> str:
        return self.__encoding

    @encoding.setter
    def encoding(self, value: str) -> None:
        try:
            'schlop'.encode(value)
            self.__encoding = value
        except LookupError:
            raise ValueError(f'"{value}" is not a correct encoding.')

    @property
    def content(self) -> list[str]:
        return self.__content

    @property
    def spaces(self) -> int:
        return self.__spaces

    @spaces.setter
    def spaces(self, value: int | str) -> None:
        tval = 0
        if type(value) is str and value.isdigit():
            tval = int(value)
        elif type(value) is int:
            tval = value
        else:
            raise TypeError('Spaces type must be int or str (digital).')
        if tval not in (1, 2, 4):
            raise ValueError('Spaces number can be 1, 2, 4.')
        self.__spaces = tval

    @property
    @abstractmethod
    def nos_type(self) -> str:
        raise NotImplementedError

    @property
    def logger(self) -> Logger:
        return self.__logger

    @logger.setter
    def logger(self, value: Logger) -> None:
        if type(value) is not Logger:
            raise ValueError('Incorrect type of a logger.')
        self.__logger = value

    @property
    @abstractmethod
    def tree(self) -> Any:
        raise NotImplementedError

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
        self.__commands_log: deque[str] = deque()
        self.__commands_index = -1

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

    def add_input_to_log(self, input: str) -> None:
        if not input:
            return
        if input in self.__commands_log:
            return
        if len(self.__commands_log) == CMD_LOG_LIMIT:
            self.__commands_log.popleft()
        self.__commands_log.append(input)
        self.__commands_index = len(self.__commands_log) - 1

    def get_input_from_log(self, *, forward: bool = True) -> str:
        result = ''
        if not self.__commands_log:
            return ''
        if forward:
            result = self.__commands_log[self.__commands_index]
            if not self.__commands_index:
                self.__commands_index = len(self.__commands_log) - 1
            else:
                self.__commands_index -= 1
        else:
            if self.__commands_index >= len(self.__commands_log) - 1:
                self.__commands_index = 0
            else:
                self.__commands_index += 1
            result = self.__commands_log[self.__commands_index]
        return result

    @abstractmethod
    def command_show(self, args: deque[str], mods: list[list[str]]) -> Response:
        raise NotImplementedError

    @abstractmethod
    def command_go(self, args: deque[str]) -> Response:
        raise NotImplementedError

    @abstractmethod
    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
        raise NotImplementedError

    @abstractmethod
    def command_up(self, args: deque[str], mods: list[list[str]]) -> Response:
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

    def mod_filter(
        self,
        data: Iterator[str] | Generator[str | Exception, None, None],
        args: list[str]
    ) -> Generator[str | Exception, None, None]:
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
                    for elem in data:
                        if type(elem) is str and regexp.search(elem):
                            yield elem.strip()
                        elif type(elem) is Exception:
                            yield elem
            except StopIteration:
                yield FabricException()

    def mod_save(
        self,
        data: Iterator[str] | Generator[str | Exception, None, None],
        args: list[str]
    ) -> Generator[str | Exception, None, None]:
        # terminating modificator
        if len(args) == 1 and data:
            destination = args[0]
            try:
                head = next(data)
                if isinstance(head, Exception):
                    yield head
                else:
                    place_to_save = destination
                    if os.path.exists(SAVES_DIR) and os.path.isdir(SAVES_DIR):
                        place_to_save = f'{SAVES_DIR}{destination}'
                    with open(place_to_save, 'w', encoding=self.encoding) as f:
                        for line in data:
                            f.write(f'{line}\n')
                        f.flush()
                        os.fsync(f.fileno())
                        yield '\n'
                        yield f'File "{place_to_save}" was successfully saved.'
            except FileNotFoundError:
                yield FabricException(f'No such file or directory for "save": {place_to_save}.')
            except StopIteration:
                yield FabricException()
        else:
            yield FabricException('Incorrect arguments for "save".')

    def mod_count(
        self,
        data: Iterator[str] | Generator[str | Exception, None, None],
        args: list[str]
    ) -> Generator[str | Exception, None, None]:
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
            yield FabricException()

    def on_enter(self, value: str) -> Response:
        self.add_input_to_log(value)
        try:
            args = reduce(  # type: ignore
                lambda acc, x: acc[:-1] + [acc[-1] + [x]] if x != '|' else acc + [[]],  # type: ignore
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
                return self.command_up(head, args[1:])
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

    @abstractmethod
    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        raise NotImplementedError

    @abstractmethod
    def get_virtual_from(self, value: str) -> str:
        raise NotImplementedError

class FabricException(Exception):
    pass
