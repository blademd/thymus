from __future__ import annotations

import re
import shlex

from functools import reduce
from collections import deque

from abc import ABC, abstractmethod
from typing import Any
from collections.abc import Iterator, Iterable

from thymus.responses import Response, SystemResponse
from thymus.lexers import CommonLexer


NAME_PATTERN = r'^[a-z][-_a-z0-9]{3,16}$'
ALIAS_PATTERN = r'^[a-z][-_a-z0-9]{1,8}$'


class FabricException(Exception):
    pass


class Context(ABC):
    __slots__ = (
        '_cid',
        '_name',
        '_content',
        '_encoding',
        '_platform_settings',
        '_neighbors',
        '_spaces',
        '_up_limit',
        '_saves_dir',
        '_alias_command_show',
        '_alias_command_go',
        '_alias_command_top',
        '_alias_command_up',
        '_alias_sub_command_filter',
        '_alias_sub_command_wildcard',
        '_alias_sub_command_stubs',
        '_alias_sub_command_sections',
        '_alias_sub_command_save',
        '_alias_sub_command_diff',
        '_alias_sub_command_contains',
        '_alias_sub_command_count',
        '_alias_sub_command_inactive',
        '_alias_sub_command_reveal',
    )
    __names_cache: list[tuple[type[Context], str]] = []

    delimiter = '^'
    lexer = CommonLexer

    # READ-ONLY PROPERTIES

    @property
    def context_id(self) -> int:
        return self._cid

    @property
    def is_built(self) -> bool:
        return hasattr(self, '_tree') and self._tree

    @property
    @abstractmethod
    def tree(self) -> Any:
        raise NotImplementedError

    @property
    @abstractmethod
    def cursor(self) -> Any:
        raise NotImplementedError

    @property
    @abstractmethod
    def path(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def path_offset(self) -> tuple[int, int]:
        raise NotImplementedError

    # CONFIGURABLE PROPERTIES

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Context name type must be "str".')

        if not re.match(NAME_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect format of name.')

        if (type(self), value) not in self.__names_cache:
            self.__names_cache.append((type(self), value))
        else:
            raise ValueError(f'The name "{value}" is already set.')

        self._name = value

    @property
    def spaces(self) -> int:
        return self._spaces

    @spaces.setter
    def spaces(self, value: int | str) -> None:
        if type(value) is str and value.isdigit():
            tval = int(value)
        elif type(value) is int:
            tval = value
        else:
            raise TypeError('Spaces type must be "int" or "str" with a number.')

        if tval not in (1, 2, 4):
            raise ValueError('Spaces number can be 1, 2, 4.')

        self._spaces = tval

    @property
    def up_limit(self) -> int:
        return self._up_limit

    @up_limit.setter
    def up_limit(self, value: int | str) -> None:
        if type(value) is str and value.isdigit():
            tval = int(value)
        elif type(value) is int:
            tval = value
        else:
            raise TypeError('Up limit type must be "int" or "str" with a number.')

        if 1 <= tval <= 16:
            self._up_limit = tval
        else:
            raise ValueError('Spaces number can be 1, 2, 4.')

    @property
    def alias_command_show(self) -> str:
        return self._alias_command_show

    @alias_command_show.setter
    def alias_command_show(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "show" command alias.')

        self._alias_command_show = value

    @property
    def alias_command_go(self) -> str:
        return self._alias_command_go

    @alias_command_go.setter
    def alias_command_go(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "go" command alias.')

        self._alias_command_go = value

    @property
    def alias_command_top(self) -> str:
        return self._alias_command_top

    @alias_command_top.setter
    def alias_command_top(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "top" command alias.')

        self._alias_command_top = value

    @property
    def alias_command_up(self) -> str:
        return self._alias_command_up

    @alias_command_up.setter
    def alias_command_up(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for an "up" command alias.')

        self._alias_command_up = value

    @property
    def alias_sub_command_filter(self) -> str:
        return self._alias_sub_command_filter

    @alias_sub_command_filter.setter
    def alias_sub_command_filter(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "filter" sub-command alias.')

        self._alias_sub_command_filter = value

    @property
    def alias_sub_command_wildcard(self) -> str:
        return self._alias_sub_command_wildcard

    @alias_sub_command_wildcard.setter
    def alias_sub_command_wildcard(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "wildcard" sub-command alias.')

        self._alias_sub_command_wildcard = value

    @property
    def alias_sub_command_stubs(self) -> str:
        return self._alias_sub_command_stubs

    @alias_sub_command_stubs.setter
    def alias_sub_command_stubs(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "stubs" sub-command alias.')

        self._alias_sub_command_stubs = value

    @property
    def alias_sub_command_sections(self) -> str:
        return self._alias_sub_command_sections

    @alias_sub_command_sections.setter
    def alias_sub_command_sections(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "sections" sub-command alias.')

        self._alias_sub_command_sections = value

    @property
    def alias_sub_command_save(self) -> str:
        return self._alias_sub_command_save

    @alias_sub_command_save.setter
    def alias_sub_command_save(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "save" sub-command alias.')

        self._alias_sub_command_save = value

    @property
    def alias_sub_command_diff(self) -> str:
        return self._alias_sub_command_diff

    @alias_sub_command_diff.setter
    def alias_sub_command_diff(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "diff" sub-command alias.')

        self._alias_sub_command_diff = value

    @property
    def alias_sub_command_contains(self) -> str:
        return self._alias_sub_command_contains

    @alias_sub_command_contains.setter
    def alias_sub_command_contains(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "contains" sub-command alias.')

        self._alias_sub_command_contains = value

    @property
    def alias_sub_command_count(self) -> str:
        return self._alias_sub_command_count

    @alias_sub_command_count.setter
    def alias_sub_command_count(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "count" sub-command alias.')

        self._alias_sub_command_count = value

    @property
    def alias_sub_command_inactive(self) -> str:
        return self._alias_sub_command_inactive

    @alias_sub_command_inactive.setter
    def alias_sub_command_inactive(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for an "inactive" sub-command alias.')

        self._alias_sub_command_inactive = value

    @property
    def alias_sub_command_reveal(self) -> str:
        return self._alias_sub_command_reveal

    @alias_sub_command_reveal.setter
    def alias_sub_command_reveal(self, value: str) -> None:
        if type(value) is not str:
            raise TypeError('Type of an alias for a sub-command must be "str".')

        if not re.match(ALIAS_PATTERN, value, re.IGNORECASE):
            raise ValueError('Incorrect value for a "reveal" sub-command alias.')

        self._alias_sub_command_reveal = value

    def __init__(
        self,
        context_id: int,
        name: str,
        content: list[str],
        encoding: str,
        neighbors: list[Context],
        saves_dir: str,
    ) -> None:
        self._cid = context_id
        self._name = name
        self._encoding = encoding
        self._content = content
        self._neighbors = neighbors
        self._saves_dir = saves_dir
        self._spaces = 2
        self._up_limit = 8
        self._alias_command_show = 'show'
        self._alias_command_go = 'go'
        self._alias_command_top = 'top'
        self._alias_command_up = 'up'
        self._alias_sub_command_filter = 'filter'
        self._alias_sub_command_wildcard = 'wildcard'
        self._alias_sub_command_stubs = 'stubs'
        self._alias_sub_command_sections = 'sections'
        self._alias_sub_command_save = 'save'
        self._alias_sub_command_diff = 'diff'
        self._alias_sub_command_contains = 'contains'
        self._alias_sub_command_count = 'count'
        self._alias_sub_command_inactive = 'inactive'
        self._alias_sub_command_reveal = 'reveal'

    def release(self) -> None:
        if (type(self), self._name) in self.__names_cache:
            self.__names_cache.remove((type(self), self._name))

    @abstractmethod
    def build(self) -> None:
        raise NotImplementedError

    # COMMANDS

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
            return SystemResponse.error('Not enough arguments for "set".')

        arg = args.popleft()
        arg = arg.lower()

        if len(args) != 1:
            return SystemResponse.error(f'There must be an argument for "set {arg}".')

        val = args.popleft()
        val = val.lower()

        try:
            setattr(self, arg, val)

        except (TypeError, ValueError) as error:
            # Received from setters
            return SystemResponse.error(str(error))

        except AttributeError:
            return SystemResponse.error(f'Unknown argument for "set": {arg}.')

        return SystemResponse.success(f'The "{arg}" setting was modified.')

    # MODS

    def mod_filter(self, data: Iterator[str | FabricException], args: list[str]) -> Iterator[str | FabricException]:
        if not data or len(args) != 1:
            yield FabricException(f'Incorrect arguments for "{self.alias_sub_command_filter}".')

        try:
            regexp = re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "{self.alias_sub_command_filter}": {args[0]}.')
        else:
            try:
                head = next(data)

                if isinstance(head, Exception):
                    yield head
                else:
                    yield '\n'

                    for element in data:
                        if type(element) is str and regexp.search(element):
                            yield element.strip()
                        elif isinstance(element, Exception):
                            yield element

            except StopIteration:
                yield FabricException()

    def mod_save(self, data: Iterator[str | FabricException], args: list[str]) -> Iterator[str | FabricException]:
        import os

        if not data or len(args) != 1:
            yield FabricException(f'Incorrect arguments for "{self.alias_sub_command_save}".')

        dest = args[0]

        try:
            head = next(data)

            if isinstance(data, Exception):
                yield head
            else:
                where_to_save = os.path.join(self._saves_dir, dest) if self._saves_dir else dest

                with open(where_to_save, 'w', encoding=self._encoding) as f:
                    for line in data:
                        assert type(line) is str
                        f.write(line + '\n')
                    f.flush()
                    os.fsync(f.fileno())

                yield '\n'
                yield f'File "{where_to_save}" saved.'

        except (FileNotFoundError, OSError) as error:
            yield FabricException(f'Failed to save "{where_to_save}": {error}.')
        except StopIteration:
            yield FabricException()

    def mod_count(self, data: Iterator[str | FabricException], args: list[str]) -> Iterator[str | FabricException]:
        if args:
            yield FabricException(f'There are no arguments for "{self.alias_sub_command_count}".')

        try:
            head = next(data)

            if isinstance(head, Exception):
                yield head
            else:
                counter = 0
                for line in data:
                    if line:
                        counter += 1

                yield '\n'
                yield f'Count: {counter}.'

        except StopIteration:
            yield FabricException()

    def on_enter(self, value: str) -> Response:
        try:
            args = reduce(  # type: ignore
                lambda acc, x: acc[:-1] + [acc[-1] + [x]] if x != '|' else acc + [[]],  # type: ignore
                shlex.split(value),
                [[]],
            )
            head = deque(args[0])  # the line before a possible pipe symbol
            command = head.popleft()
            if command == self.alias_command_show:
                return self.command_show(head, args[1:])
            elif command == self.alias_command_go:
                return self.command_go(head)
            elif command == self.alias_command_top:
                return self.command_top(head, args[1:])
            elif command == self.alias_command_up:
                return self.command_up(head, args[1:])
            if command == 'set':
                return self.command_set(head)
            else:
                return SystemResponse.error(f'Unknown command "{command}".')

        except IndexError:
            return SystemResponse.error('Command failed.')

        except ValueError:
            return SystemResponse.error('Command failed.')

        except NotImplementedError:
            return SystemResponse.error(f'The method for "{command}" is not implemented yet.')

    @abstractmethod
    def get_rollback_config(self, virtual_path: str) -> tuple[int, int, Iterable[str]]:  # TODO: modify the descr
        """Method calculates a block of config that belongs to the specified path and returns numbers of the first
        and last lines with the block itself.

        If the virtual_path is not root, begin is incremented to skip the first line. For the root, end is incremented
        to account for the last line (i.e., feed the full config).

        Returns:
            (begin, end, iter(config[begin:end]))
        """
        raise NotImplementedError

    @abstractmethod
    def get_possible_sections(self, value: str) -> Iterator[str]:
        raise NotImplementedError

    def get_possible_commands(self, value: str) -> Iterator[str]:
        commands = (
            self.alias_command_go,
            self.alias_command_show,
            self.alias_command_top,
            self.alias_command_up,
            'edit',
            'set',
        )

        sorted_commands = []

        for command in commands:
            if command.startswith(value):
                sorted_commands.append(command)

        yield from sorted_commands

    @abstractmethod
    def get_virtual_from(self, value: str) -> str:
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def validate_commit(commit_data: Iterable[str]) -> None:
        raise NotImplementedError
