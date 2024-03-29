from __future__ import annotations

import sys
import re

from typing import TYPE_CHECKING, Optional
from collections import deque
from itertools import chain
from difflib import Differ
from copy import copy

if sys.version_info.major == 3 and sys.version_info.minor >= 9:
    from collections.abc import Generator, Iterable, Iterator
else:
    from typing import Generator, Iterable, Iterator

from thymus_ast.ios import (  # type: ignore
    Root,
    Node,
    construct_tree,
    analyze_heuristics,
    lazy_provide_config,
    search_node,
    search_h_node,
)

from .context import (
    Context,
    FabricException,
    UP_LIMIT,
)
from ..responses import (
    Response,
    ContextResponse,
    AlertResponse,
)
from ..lexers import IOSLexer
from ..misc import find_common


if TYPE_CHECKING:
    from logging import Logger


class IOSContext(Context):
    __slots__ = (
        '_tree',
        '_cursor',
        '_virtual_cursor',
        '_virtual_h_cursor',
        '_is_heuristics',
        '_is_base_heuristics',
        '_is_crop',
        '_is_promisc',
    )
    __store: list[IOSContext] = []
    lexer: type[IOSLexer] = IOSLexer

    @property
    def prompt(self) -> str:
        if self._cursor.name == 'root':
            return ''
        else:
            return self._cursor.path

    @property
    def tree(self) -> Root:
        return self._tree

    @property
    def nos_type(self) -> str:
        return 'IOS'

    @property
    def heuristics(self) -> bool:
        return self._is_heuristics

    @heuristics.setter
    def heuristics(self, value: str | int | bool) -> None:
        if type(value) is bool:
            self._is_heuristics = value
        elif type(value) is str:
            if value in ('0', 'off'):
                self._is_heuristics = False
            elif value in ('1', 'on'):
                if self._is_heuristics and hasattr(self, '_tree') and self._tree:
                    raise ValueError('The heuristics mode is already active.')
                self._is_heuristics = True
                if hasattr(self, '_tree') and self._tree:
                    analyze_heuristics(self._tree, self._tree.delimiter, self._is_crop)
            else:
                raise ValueError(f'Unknown value for heuristics: {value}.')
        elif type(value) is int:
            if value == 0:
                self._is_heuristics = False
            elif value == 1:
                if self._is_heuristics:
                    raise ValueError('The heuristics mode is already active.')
                self._is_heuristics = True
                if hasattr(self, '_tree') and self._tree:
                    analyze_heuristics(self._tree, self._tree.delimiter, self._is_crop)
            else:
                raise ValueError(f'Unknown value for heuristics: {value}.')
        else:
            raise TypeError(f'Incorrect type for heuristics: {type(value)}.')

    @property
    def base_heuristics(self) -> bool:
        return self._is_base_heuristics

    @base_heuristics.setter
    def base_heuristics(self, value: str | int | bool) -> None:
        if type(value) is bool:
            self._is_base_heuristics = value
        elif type(value) is str:
            if value in ('0', 'off'):
                self._is_base_heuristics = False
            elif value in ('1', 'on'):
                if self._is_base_heuristics and hasattr(self, '_tree') and self._tree:
                    raise ValueError('The base heuristics mode is already active.')
                self._is_base_heuristics = True
            else:
                raise ValueError(f'Unknown value for base heuristics: {value}.')
        elif type(value) is int:
            if value == 0:
                self._is_base_heuristics = False
            elif value == 1:
                if self._is_base_heuristics:
                    raise ValueError('The base heuristics mode is already active.')
                self._is_base_heuristics = True
            else:
                raise ValueError(f'Unknown value for base heuristics: {value}.')
        else:
            raise TypeError(f'Incorrect type for base heuristics: {type(value)}.')
        if hasattr(self, '_tree') and self._tree:
            self._rebuild_tree()

    @property
    def crop(self) -> bool:
        return self._is_crop

    @crop.setter
    def crop(self, value: str | int | bool) -> None:
        if hasattr(self, '_tree') and self._tree and not self._is_heuristics:
            raise ValueError('The heuristics mode must be present and enabled first.')
        if type(value) is bool:
            self._is_crop = value
        elif type(value) is str:
            if value in ('0', 'off'):
                self._is_crop = False
            elif value in ('1', 'on'):
                self._is_crop = True
            else:
                raise ValueError(f'Unknown value for crop: {value}.')
        elif type(value) is int:
            if value == 0:
                self._is_crop = False
            elif value == 1:
                self._is_crop = True
            else:
                raise ValueError(f'Unknown value for crop: {value}.')
        else:
            raise TypeError(f'Incorrect type for crop: {type(value)}.')
        if hasattr(self, '_tree') and self._tree and self._is_heuristics:
            self._rebuild_tree()

    @property
    def promisc(self) -> bool:
        return self._is_promisc

    @promisc.setter
    def promisc(self, value: str | int | bool) -> None:
        if type(value) is bool:
            self._is_promisc = value
        elif type(value) is str:
            if value in ('0', 'off'):
                self._is_promisc = False
            elif value in ('1', 'on'):
                self._is_promisc = True
            else:
                raise ValueError(f'Unknown value for promisc: {value}.')
        elif type(value) is int:
            if value == 0:
                self._is_promisc = False
            elif value == 1:
                self._is_promisc = True
            else:
                raise ValueError(f'Unknown value for promisc: {value}.')
        else:
            raise TypeError(f'Incorrect type for promisc: {type(value)}.')

    def __init__(
        self, name: str, content: list[str], *, encoding: str, settings: dict[str, str | int], logger: Logger
    ) -> None:
        self._is_heuristics = False
        self._is_base_heuristics = True
        self._is_crop = False
        self._is_promisc = False
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)
        self._tree: Root = construct_tree(
            config=self.content,
            delimiter=self.delimiter,
            is_heuristics=self._is_heuristics,
            is_base_heuristics=self._is_base_heuristics,
            is_crop=self._is_crop,
            is_promisc=self._is_promisc,
        )
        if not self._tree:
            raise Exception(f'Impossible to build a tree for "{self.nos_type}".')
        self.__store.append(self)
        self._cursor: Root | Node = self._tree
        self._virtual_cursor: Root | Node = self._tree
        self._virtual_h_cursor: Root | Node = self._tree
        if 'end' not in self.keywords['top']:
            self.keywords['top'].append('end')
        if 'exit' not in self.keywords['up']:
            self.keywords['up'].append('exit')
        if 'include' not in self.keywords['filter']:
            self.keywords['filter'].append('include')

    def _rebuild_tree(self) -> None:
        self._tree = None
        self._cursor = None
        self._tree = construct_tree(
            config=self.content,
            delimiter=self.delimiter,
            is_heuristics=self._is_heuristics,
            is_base_heuristics=self._is_base_heuristics,
            is_crop=self._is_crop,
            is_promisc=self._is_promisc,
        )
        self._cursor = self._tree
        self.logger.debug(f'The tree was rebuilt. {self.nos_type}.')

    def _get_node_content(self, node: Root | Node) -> Generator[str, None, None]:
        return lazy_provide_config(self.content, node, alignment=self.spaces, is_started=True)

    def _prepand_nop(self, data: Iterable[str]) -> Generator[str | Exception, None, None]:
        """
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by _process_fabric method or __mod methods. Final stream does not contain it.
        """
        yield '\n'
        yield from data

    def _inspect_children_pair(self, node: Root | Node, parent_path: str) -> Generator[tuple[str, Node], None, None]:
        for child in node.children:
            if child.is_accessible:
                path = child.path.replace(parent_path, '').replace(self.delimiter, ' ').strip()
                yield path, child
            else:
                yield from self._inspect_children_pair(child, parent_path)

    def _inspect_children_path(self, node: Root | Node, parent_path: str) -> Generator[str, None, None]:
        for child in node.children:
            if child.is_accessible:
                yield child.path.replace(parent_path, '').replace(self.delimiter, ' ').strip()
            else:
                yield from self._inspect_children_path(child, parent_path)

    def _update_virtual_cursor(self, parts: deque[str], *, is_heuristics: bool = False) -> Generator[str, None, None]:
        # is_heuristics here is a marker that sports which cursor and its nodes to use
        target = self._virtual_h_cursor.heuristics if is_heuristics else self._virtual_cursor.children
        head = parts.popleft()
        if head == '|':
            yield from map(lambda x: x.name, target)
        for child in target:
            # We ignore `is_accessible` flag because the virtual cursors are actually virtual.
            if child.name == head:
                if is_heuristics:
                    self._virtual_h_cursor = child
                else:
                    self._virtual_cursor = child
                if parts:
                    yield from self._update_virtual_cursor(parts, is_heuristics=is_heuristics)
                else:
                    yield from filter(lambda x: x.lower().startswith(head), map(lambda x: x.name, target))
                return
        # a child wasn't found
        # so we try to get all matches instead
        yield from filter(lambda x: x.lower().startswith(head), map(lambda x: x.name, target))

    def free(self) -> None:
        self.__store.remove(self)
        super().free()

    def apply_settings(self, settings: dict[str, str | int]) -> None:
        if hasattr(self, '_tree') and self._tree:
            self.logger.debug('Trying to apply settings with a completed tree.')
            return
        super().apply_settings(settings)

    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        """
        This method receives a value from user's input symbol by symbol
            and tries to guess the next possible path(s) for this input.
        """
        if not value:
            return
        value = value.lower()
        parts: list[str] = value.split()
        command: str = parts[0]  # command must be top, show, or go
        sub_command: str = ''
        offset: int = 0
        if command in self.keywords['top']:
            if len(parts) < 3:
                return
            sub_command = parts[1]  # sub_command must be show or go
            if sub_command in self.keywords['show'] or sub_command in self.keywords['go']:
                self._virtual_cursor = self._tree
                self._virtual_h_cursor = self._tree
                offset = 2
                command = sub_command
            else:
                return
        elif command in self.keywords['up']:
            if len(parts) < 3:
                return
            sub_command = parts[1]  # sub_command must be show or go
            if sub_command in self.keywords['show'] or sub_command in self.keywords['go']:
                temp = self._cursor
                self.command_up(deque(), [])
                self._virtual_cursor = self._cursor
                self._virtual_h_cursor = self._cursor
                self._cursor = temp
                offset = 2
                command = sub_command
            else:
                return
        elif command in self.keywords['show'] or command in self.keywords['go']:
            if len(parts) < 2:
                return
            self._virtual_cursor = self._cursor
            self._virtual_h_cursor = self._cursor
            offset = 1
        else:
            return
        data = deque(parts[offset:])
        if self._is_heuristics and command not in self.keywords['go']:
            yield from chain(
                self._update_virtual_cursor(copy(data), is_heuristics=False),
                self._update_virtual_cursor(copy(data), is_heuristics=True),
            )
        else:
            yield from self._update_virtual_cursor(data, is_heuristics=False)

    def get_virtual_from(self, value: str) -> str:
        """
        This method receives a value from user's input after a Tab's strike and returns
            a word that should be replaced in the input.
        """
        if not value:
            return ''
        parts: list[str] = value.split()
        first = ''
        command = parts[0]
        if command in self.keywords['top'] or command in self.keywords['up']:
            if len(parts) < 3:
                return ''
            first = command
            parts = parts[2:]
        elif command in self.keywords['show'] or command in self.keywords['go']:
            if len(parts) < 2:
                return ''
            parts = parts[1:]
        else:
            return ''
        input = ' '.join(parts)
        current_path = self._cursor.path.replace(self.delimiter, ' ')
        virtual_path = self._virtual_cursor.path.replace(self.delimiter, ' ')
        hvirtual_path = self._virtual_h_cursor.path.replace(self.delimiter, ' ')
        temp = self._cursor
        if first == 'up':
            self.command_up(deque(), [])
            current_path = self._cursor.path.replace(self.delimiter, ' ')
        if current_path:
            # shorten the virtual paths
            virtual_path = virtual_path.replace(current_path, '', 1)
            hvirtual_path = hvirtual_path.replace(current_path, '', 1)
        self._cursor = temp
        virtual_path = virtual_path.strip().lower()
        hvirtual_path = hvirtual_path.strip().lower()
        # here we need to find out which virtual path has more in common with the input
        first = find_common([virtual_path, input])
        second = find_common([hvirtual_path, input])
        if len(first) == len(second) or len(first) > len(second):
            return input.replace(first, '', 1)
        else:
            return input.replace(second, '', 1)

    def mod_stubs(self, jump_node: Optional[Node] = None) -> Generator[str | Exception, None, None]:
        node = self._cursor if not jump_node else jump_node
        if not node.stubs:
            yield FabricException('No stubs at this level.')
        yield '\n'  # nop
        yield from node.stubs

    def mod_sections(self, jump_node: Optional[Node] = None) -> Generator[str | Exception, None, None]:
        node = self._cursor if not jump_node else jump_node
        if not node.children:
            yield FabricException('No sections at this level.')
        yield '\n'
        yield from self._inspect_children_path(node, node.path)

    def mod_wildcard(
        self,
        data: Iterator[str] | Generator[str | Exception, None, None],
        args: list[str],
        jump_node: Optional[Node] = None,
    ) -> Generator[str | Exception, None, None]:
        if not data or len(args) != 1:
            yield FabricException('Incorrect arguments for "wildcard".')
        try:
            regexp = re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "wildcard": {args[0]}.')
        else:
            try:
                head = next(data)
                if isinstance(head, Exception):
                    yield head
                else:
                    node = jump_node if jump_node else self._cursor
                    if not node.children:
                        yield FabricException('No sections at this level.')
                    yield '\n'
                    for path, child in self._inspect_children_pair(node, node.path):
                        self.logger.debug(f'{path} {child.name}')
                        if re.search(regexp, path):
                            yield from self._get_node_content(child)
            except StopIteration:
                yield FabricException()

    def mod_diff(self, args: list[str], jump_node: Optional[Node] = None) -> Generator[str | Exception, None, None]:
        if len(args) != 1:
            yield FabricException('There must be one argument for "diff".')
        if not self.name:
            yield FabricException('Please use "set name" to name this context first.')
        if len(self.__store) <= 1:
            yield FabricException('No other contexts.')
        context_name = args[0]
        if self.name == context_name:
            yield FabricException("You can't compare the same context.")
        remote_context: Optional[Context] = None
        for elem in self.__store:
            if elem.name == context_name and type(elem) is type(self):
                remote_context = elem
                break
        else:
            yield FabricException('Remote context has not been found.')
        assert remote_context is not None  # mypy's satisfier
        target: Root | Node = None
        peer: Root | Node = None
        if jump_node:
            target = jump_node
            path = deque(jump_node.path.split(self.delimiter))
            peer = search_node(path, remote_context.tree)
        else:
            target = self._cursor
            if target.name != 'root':
                path = deque(target.path.split(self.delimiter))
                peer = search_node(path, remote_context.tree)
            else:
                peer = remote_context.tree
        if not peer:
            yield FabricException(f'Remote context lacks this path: {target.path.replace(self.delimiter, " ")}.')
        yield '\n'
        yield from Differ().compare(
            list(lazy_provide_config(self.content, target, self.spaces)),
            list(lazy_provide_config(remote_context.content, peer, remote_context.spaces)),
        )

    def mod_contains(self, args: list[str], jump_node: Optional[Node] = []) -> Generator[str | Exception, None, None]:
        def replace_path(source: str, head: str) -> str:
            return source.replace(head, '').replace(self.delimiter, ' ').strip()

        def lookup_child(node: Node, path: str = '') -> Generator[str, None, None]:
            for child in node.children:
                yield from lookup_child(child, path)
            if not node.is_accessible:
                return
            if re.search(args[0], node.path.replace(self.delimiter, ' ')):
                yield replace_path(node.path, path)
            for stub in filter(lambda x: re.search(args[0], x), node.stubs):
                yield f'{replace_path(node.path, path)}: "{stub}"' if node.path else f'"{stub}"'

        if len(args) != 1:
            yield FabricException('There must be one argument for "contains".')
        node = self._cursor if not jump_node else jump_node
        if not node.children:
            yield FabricException('No sections at this level.')
        try:
            re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "contains": {args[0]}.')
        yield '\n'
        yield from lookup_child(node, node.path)

    def _process_fabric(
        self, data: Iterable[str], mods: list[list[str]], *, jump_node: Optional[Node] = None
    ) -> Response:
        def check_leading_mod(name: str, position: int, args_count: int, args_limit: int = 0) -> None:
            if position:
                raise FabricException(f'Incorrect position of "{name}".')
            if args_count != args_limit:
                raise FabricException(f'Incorrect number of arguments for "{name}". Must be {args_limit}.')

        recol_data = self._prepand_nop(data)
        try:
            for number, elem in enumerate(mods):
                command = elem[0]
                if command in self.keywords['filter']:
                    recol_data = self.mod_filter(recol_data, elem[1:])
                elif command in self.keywords['stubs']:
                    check_leading_mod(command, number, len(elem[1:]))
                    recol_data = self.mod_stubs(jump_node)
                elif command in self.keywords['sections']:
                    check_leading_mod(command, number, len(elem[1:]))
                    recol_data = self.mod_sections(jump_node)
                elif command in self.keywords['save']:
                    recol_data = self.mod_save(recol_data, elem[1:])
                    break
                elif command in self.keywords['count']:
                    recol_data = self.mod_count(recol_data, elem[1:])
                    break
                elif command in self.keywords['wildcard']:
                    recol_data = self.mod_wildcard(recol_data, elem[1:], jump_node)
                elif command in self.keywords['diff']:
                    check_leading_mod(command, number, len(elem[1:]), 1)
                    recol_data = self.mod_diff(elem[1:], jump_node)
                elif command in self.keywords['contains']:
                    check_leading_mod(command, number, len(elem[1:]), 1)
                    recol_data = self.mod_contains(elem[1:], jump_node)
                else:
                    raise FabricException(f'Unknown modificator "{command}".')
            head = next(recol_data)
            if isinstance(head, Exception):
                raise head
            return ContextResponse.success(recol_data)
        except (AttributeError, IndexError) as err:
            return AlertResponse.error(f'Unknown error from the fabric #001: {err}')
        except FabricException as err:
            return AlertResponse.error(f'{err}')
        except StopIteration:
            return AlertResponse.error('Unknown error from the fabric #002.')
        except Exception as err:
            self.logger.error(str(err))
            return AlertResponse.error('Unknwown error. See the log.')

    def command_show(self, args: deque[str], mods: list[list[str]]) -> Response:
        if args:
            first_arg = args[0]
            if first_arg in self.keywords['version']:
                if len(args) > 1:
                    return AlertResponse.error('Too many arguments for "version".')
                if self._tree.version:
                    return ContextResponse.success(self._tree.version)
                return AlertResponse.error('No version has been found.')
            else:
                hpath = copy(args)
                if node := search_node(args, self._cursor):
                    if mods:
                        return self._process_fabric(self._get_node_content(node), mods, jump_node=node)
                    else:
                        return ContextResponse.success(self._get_node_content(node))
                else:
                    if self._is_heuristics:
                        if hnode := search_h_node(hpath, self._cursor):
                            return ContextResponse.success(hnode.stubs)
                    return AlertResponse.error('This path is not correct.')
        else:
            if mods:
                return self._process_fabric(self._get_node_content(self._cursor), mods)
            else:
                return ContextResponse.success(self._get_node_content(self._cursor))

    def command_go(self, args: deque[str]) -> Response:
        if not args:
            return AlertResponse.error('Not enough arguments for "go".')
        if node := search_node(args, self._cursor):
            self._cursor = node
            return AlertResponse.success()
        return AlertResponse.error('This path is not correct.')

    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
        if args:
            sub_command = args.popleft()
            temp = self._cursor
            self._cursor = self._tree
            if sub_command in self.keywords['show']:
                result = self.command_show(args, mods)
                self._cursor = temp
                return result
            elif sub_command in self.keywords['go']:
                result = self.command_go(args)
                if not result.is_ok:
                    self._cursor = temp
                    return AlertResponse.error(result.value)
                return AlertResponse.success()
            else:
                self._cursor = temp
                return AlertResponse.error(f'Incorrect sub-command for "top": {sub_command}.')
        else:
            self._cursor = self._tree
            return AlertResponse.success()

    def command_up(self, args: deque[str], mods: list[list[str]]) -> Response:
        steps: int = 1
        if args:
            arg = args.popleft()
            if arg in self.keywords['show']:
                if self._cursor.name == 'root':
                    return AlertResponse.error("You can't do a negative lookahead from the top.")
                temp = self._cursor
                self.command_up(deque(), [])
                result = self.command_show(args, mods)
                self._cursor = temp
                return result
            elif arg.isdigit():
                if len(args) != 1:
                    return AlertResponse.error('There must be one argument for "up".')
                steps = min(int(arg), UP_LIMIT)
            else:
                return AlertResponse.error(f'Incorrect argument for "up": {arg}.')
        if self._cursor.name == 'root':
            return AlertResponse.success()
        current = self._cursor
        while steps:
            if current.name == 'root':
                break
            current = current.parent
            if current.is_accessible:
                steps -= 1
        self._cursor = current
        return AlertResponse.success()
