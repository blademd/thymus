from __future__ import annotations

import sys
import re
import shlex
import os

from ..parsers.jparser import (
    construct_tree,
    lazy_parser,
    lazy_provide_config,
    lazy_wc_parser,
    search_node,
    compare_nodes,
    search_inactives,
    draw_inactive_tree,
    draw_diff_tree,
)

from typing import TYPE_CHECKING, NoReturn
from collections import deque
from functools import reduce


if TYPE_CHECKING:
    from ..parsers.jparser import (
        Root,
        Node,
    )
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Generator, Iterable, Callable
    else:
        from typing import Generator, Iterable, Callable


class Context:
    __slots__ = (
        '__name',
        '__content',
        '__encoding',
    )

    delimiter: str = '^'

    def __init__(self, name: str, content: list[str], encoding='utf-8-sig') -> None:
        self.__name = name
        self.__content = content
        self.__encoding = encoding

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

    @name.setter
    def name(self, value: str) -> None:
        if type(value) is not str or not re.match(r'^[0-9a-z]{4,8}$', value, re.I):
            raise ValueError('Incorrect format of a name: use only these 0-9 or a-z.\nFrom 4 to 8 symbols.')
        self.__name = value

    @encoding.setter
    def encoding(self, value: str) -> None:
        try:
            'shlop'.encode(value)
            self.__encoding = value
        except LookupError:
            raise ValueError(f'{value} is not a correct encoding.')

    def on_enter(self, value: str) -> 'Iterable[str]':
        pass

    def update_virtual(self, value: str) -> 'Generator[str, None, None]':
        pass

    def get_virtual_from(self, value: str) -> str:
        pass

class FabricException(Exception):
    pass

class JunosContext(Context):
    __slots__ = (
        '__tree',
        '__cursor',
        '__virtual_cursor',
        '__spaces',
    )
    __commands = (
        'go',
        'show',
    )
    __store: list[JunosContext] = []

    def __init__(self, name: str, content: list[str], encoding='utf-8-sig') -> None:
        super().__init__(name, content, encoding)
        self.__tree: 'Root' = construct_tree(self.content)
        if not self.__tree or not self.__tree.get('children'):
            raise Exception('Impossible to build the tree.')
        self.__cursor: 'Root | Node' = self.__tree
        self.__virtual_cursor: 'Root | Node' = self.__tree
        self.__spaces: int = 2
        self.__store.append(self)

    @property
    def prompt(self) -> str:
        if self.__cursor['name'] == 'root':
            return ''
        else:
            return self.__cursor['path']

    @property
    def tree(self) -> 'Root':
        return self.__tree

    @property
    def spaces(self) -> int:
        return self.__spaces

    @spaces.setter
    def spaces(self, value: int) -> None:
        if value not in (2, 4, 8):
            raise ValueError('Spaces number can be 2, 4, or 8.')
        self.__spaces = value

    def on_enter(self, value: str) -> 'Iterable[str]':
        if not value:
            return
        args = reduce(
            lambda acc, x: acc[:-1] + [acc[-1] + [x]] if x != '|' else acc + [[]],
            shlex.split(value),
            [[]]
        )
        head = deque(args[0])  # the line before a possible pipe symbol
        command = head.popleft()
        if command == 'show':
            return self.__command_show(head, args[1:])
        elif command == 'go':
            return self.__command_go(head)
        elif command == 'top':
            return self.__command_top(head, args[1:])
        elif command == 'up':
            return self.__command_up(head)
        elif command == 'set':
            return self.__command_set(head)
        return []

    def __update_virtual_from_cursor(self, parts: list[str]) -> 'Generator[str, None, None]':
        if not parts:
            return
        for child in self.__virtual_cursor['children']:
            if child['name'] == parts[0]:
                self.__virtual_cursor = child
                if parts[1:]:
                    yield from self.__update_virtual_from_cursor(parts[1:])
                break
            elif (len(parts) > 1 and child['name'] == ' '.join(parts[:2])):
                self.__virtual_cursor = child
                if parts[2:]:
                    yield from self.__update_virtual_from_cursor(parts[2:])
                break
        else:
            value = parts[0]
            if len(parts) > 1:
                value = f'{parts[0]} {parts[1]}'
            for child in self.__virtual_cursor['children']:
                if child['name'].startswith(value):
                    yield child['name']

    def update_virtual(self, value: str) -> 'Generator[str, None, None]':
        if not value:
            return
        # little bit hacky here
        if m := re.search(r'([-a-z0-9\/]+)\.(\d+)', value, re.I):
            value = value.replace(f'{m.group(1)}.{m.group(2)}', f'{m.group(1)} unit {m.group(2)}')
        parts = value.split()
        if parts[0] == 'top':
            if len(parts) == 2 and parts[1] in self.__commands:
                # for child in self.__tree['children']:
                #     yield child['name']
                pass
            elif len(parts) > 2 and parts[1] in self.__commands:
                self.__virtual_cursor = self.__tree
                yield from self.__update_virtual_from_cursor(parts[2:])
        elif parts[0] in self.__commands:
            if len(parts) == 1:
                # for child in self.__virtual_cursor['children']:
                #     yield child['name']
                pass
            else:
                self.__virtual_cursor = self.__cursor
                yield from self.__update_virtual_from_cursor(parts[1:])

    def get_virtual_from(self, value: str) -> str:
        # little bit hacky here
        if m := re.search(r'([-a-z0-9\/]+)\.(\d+)', value, re.I):
            value = value.replace(f'{m.group(1)}.{m.group(2)}', f'{m.group(1)} unit {m.group(2)}')
        parts = value.split()
        if len(parts) < 2:
            return ''
        if parts[0] == 'top':
            if len(parts) < 3:
                return ''
            parts = parts[1:]
        if parts[0] not in self.__commands:
            return ''
        new_value = ' '.join(parts[1:])
        if self.__virtual_cursor['name'] == 'root':
            return new_value
        path = self.__virtual_cursor['path']
        if self.__cursor['name'] != 'root':
            path = path.replace(self.__cursor['path'], '')
        path = path.replace(self.delimiter, ' ')
        path = path.strip()
        if new_value.startswith(path):
            return new_value.replace(path, '')
        return new_value

    def __filter(self, args: deque[str], source: 'Iterable[str]') -> 'Generator[str, None, None]':
        # passthrough modificator
        if len(args) != 1 or not source:
            raise FabricException('Incorrect arguments for `filter`.')
        try:
            regexp = re.compile(args.pop())
        except re.error:
            raise FabricException('Incorrect expression for `filter`.')
        else:
            for line in filter(lambda x: regexp.search(x), source):
                yield line

    def __wc_filter(self, args: deque[str], source: 'Iterable[str]') -> 'Generator[str, None, None]':
        # passthrough modificator
        if len(args) != 1 or not source:
            raise FabricException('Incorrect arguments for `wc_filter`.')
        return lazy_wc_parser(source, '', args.pop())

    def __save(self, args: deque[str], source: 'Iterable[str]') -> NoReturn:
        # terminating modificator
        if len(args) == 1 and source:
            destination = args.pop()
            with open(destination, 'w', encoding=self.encoding) as f:
                for line in source:
                    f.write(f'{line}\n')
                f.flush()
                os.fsync(f.fileno())
                raise FabricException()
        raise FabricException('Incorrect arguments for `save`.')

    def __count(self, args: deque[str], source: 'Iterable[str]') -> NoReturn:
        # terminating modificator
        if args:
            raise FabricException('Incorrect arguments for `count`.')
        counter = 0
        for _ in filter(lambda x: x, source):
            counter += 1
        raise FabricException(f'Count: {counter}')

    def header(method: 'Callable') -> 'Callable':
        # for leading passthrough modificators only
        def inner(self: JunosContext, args: deque[str], extra_args: deque[str] = []) -> 'Generator[str, None, None]':
            if args:
                raise FabricException('Syntax error for the leading modificator: too many args.')
            node = self.__cursor
            if extra_args:
                path = extra_args.pop()
                node = search_node(deque(path.split(self.delimiter)), self.__tree)
            yield from method(node)
        return inner

    def __compare(self, args: deque[str], extra_args: deque[str] = []) -> 'Generator[str, None, None]':
        # leading passthrough modificator
        if len(args) != 1:
            raise FabricException('Incorrect arguments for `comapare`.')
        context_name = args.pop()
        if context_name == self.name:
            raise FabricException('You can`t compare the same context.')
        if not self.name:
            raise FabricException('Please `set name` for this context.')
        if len(self.__store) <= 1:
            raise FabricException('No other contexts.')
        remote_context: JunosContext | None = None
        for context in self.__store:
            if context.name == context_name:
                remote_context = context
                break
        else:
            raise FabricException('Target context was not found.')
        target: 'Root | Node' = {}
        peer: 'Root | Node' = {}
        if not extra_args:
            target = self.__cursor
            if self.__cursor['name'] != 'root':
                path = self.prompt
                peer = search_node(deque(path.split(self.delimiter)), remote_context.tree)
            else:
                peer = remote_context.tree
        else:
            path = extra_args.pop()
            target = search_node(deque(path.split(self.delimiter)), self.__tree)
            peer = search_node(deque(path.split(self.delimiter)), remote_context.tree)
        if not peer:
            raise FabricException('Incorrect path for peer`s context.')
        tree = compare_nodes(target, peer)
        return draw_diff_tree(tree, tree['name'])

    @header
    def __inactive(node: 'Root | Node') -> 'Generator[str, None, None]':
        tree = search_inactives(node)
        return draw_inactive_tree(tree, tree['name'])

    @header
    def __stubs(node: 'Root | Node') -> 'Iterable[str]':
        if not node.get('stubs'):
            raise FabricException('No stubs at this level.')
        return iter(node['stubs'])

    @header
    def __sections(node: 'Root | Node') -> 'Generator[str, None, None]':
        if not node.get('children'):
            raise FabricException('No sections at this level.')
        for child in node['children']:
            yield child['name']

    def __process_fabric(
        self,
        mods: list[list[str]],
        source: 'Iterable[str]',
        extra_args: deque[str] = []
    ) -> 'Generator[str, None, None]':
        data = source
        is_flat_output = True
        try:
            for index, element in enumerate(mods):
                command = element[0]
                if command == 'filter':
                    data = self.__filter(deque(element[1:]), data)
                elif command == 'wc_filter':
                    data = self.__wc_filter(deque(element[1:]), data)
                    is_flat_output = False
                elif command == 'save':
                    data = lazy_provide_config(data, block=' ' * self.spaces)
                    data = self.__save(deque(element[1:]), data)
                elif command == 'count':
                    data = self.__count(deque(element[1:]), data)
                elif command == 'compare':
                    if index:
                        raise FabricException('Incorrect position of `compare`.')
                    data = self.__compare(deque(element[1:]), extra_args)
                    is_flat_output = False
                elif command == 'inactive':
                    if index:
                        raise FabricException('Incorrect position of `inactive`.')
                    data = self.__inactive(deque(element[1:]), extra_args)
                    is_flat_output = False
                elif command == 'stubs':
                    if index:
                        raise FabricException('Incorrect position of `stubs`.')
                    data = self.__stubs(deque(element[1:]), extra_args)
                elif command == 'sections':
                    if index:
                        raise FabricException('Incorrect position of `sections`.')
                    data = self.__sections(deque(element[1:]), extra_args)
                else:
                    raise FabricException('Unknown modificator.')
            if not data:
                return
            if is_flat_output:
                for line in data:
                    yield line.strip()
            else:
                yield from lazy_provide_config(data, block=' ' * self.spaces)
        except (AttributeError, IndexError):
            pass
        except FabricException as err:
            if len(err.args):
                yield err.args[0]

    def __command_show(self, args: deque[str] = [], mods: list[list[str]] = []) -> 'Iterable[str]':
        if args:
            if args[0] in ('ver', 'version',):
                if len(args) > 1:
                    return iter(['Incorrect arguments for `show version`.'])
                ver = self.__tree['version'] if self.__tree['version'] else 'No version has been detected.'
                return iter([ver])
            else:
                if node := search_node(args, self.__cursor):
                    data = lazy_parser(self.content, node['path'], self.delimiter)
                    next(data)
                    if mods:
                        args.append(node['path'])
                        return self.__process_fabric(mods, data, extra_args=args)
                    else:
                        return lazy_provide_config(data, block=' ' * self.spaces)
                else:
                    return iter(['The path is not correct.'])
        else:
            data = iter(self.content)
            if self.__cursor['name'] != 'root':
                data = lazy_parser(data, self.__cursor['path'], self.delimiter)
                next(data)
            if mods:
                return self.__process_fabric(mods, data)
            else:
                return lazy_provide_config(data, block=' ' * self.spaces)

    def __command_go(self, args: deque[str]) -> 'Iterable[str]':
        if not args:
            return iter(['Incorrect arguments for `go`.'])
        if node := search_node(args, self.__cursor):
            self.__cursor = node
        else:
            return iter(['The path is not correct.'])
        return []

    def __command_top(self, args: deque[str] = [], mods: list[list[str]] = []) -> 'Iterable[str]':
        if args and len(args) < 2:
            return iter(['Incorrect arguments for `top`.'])
        if args:
            command = args.popleft()
            if command == 'show':
                temp = self.__cursor
                self.__cursor = self.__tree
                result = self.__command_show(args, mods)
                self.__cursor = temp
                return result
            elif command == 'go':
                temp = self.__cursor
                self.__cursor = self.__tree
                if self.__command_go(args):
                    self.__cursor = temp
            else:
                return iter(['Incorrect arguments for `top`.'])
        else:
            if self.__cursor['name'] == 'root':
                return []
            self.__cursor = self.__tree
        return []

    def __command_up(self, args: deque[str] = []) -> 'Iterable[str]':
        if args and len(args) != 1:
            return iter(['Incorrect arguments for `up`.'])
        if args and len(args[0]) > 2:
            return iter(['Incorrect length for `up`.'])
        steps_back = 1
        if args:
            if args[0].isdigit():
                steps_back = int(args[0])
            else:
                return iter(['Incorrect arguments for `up`.'])
        if self.__cursor['name'] == 'root':
            return []
        node = self.__cursor
        while steps_back:
            if node['name'] == 'root':
                break
            node = node['parent']
            steps_back -= 1
        self.__cursor = node
        return []

    def __command_set(self, args: deque[str]) -> 'Iterable[str]':
        if not args:
            return iter(['Incorrect arguments for `set`.'])
        command = args.popleft()
        if command in ('name', 'spaces', 'encoding',):
            if len(args) != 1:
                return iter([f'Incorrect arguments for `set {command}`.'])
            value = args.pop()
            try:
                if command == 'name':
                    self.name = value
                elif command == 'spaces':
                    self.spaces = int(value)
                elif command == 'encoding':
                    self.encoding = value
            except ValueError as err:
                if len(err.args):
                    return iter(err.args)
            else:
                return iter([f'The {command} was successfully set.'])
        else:
            return iter(['Unknow argument for `set`.'])
        return []
