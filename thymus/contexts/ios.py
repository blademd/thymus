from __future__ import annotations

from typing import TYPE_CHECKING
from collections import deque
from itertools import chain
from difflib import Differ
from copy import copy

from .context import (
    Context,
    FabricException,
    UP_LIMIT,
)
from ..responses import (
    ContextResponse,
    AlertResponse,
)
from ..parsers.ios import (
    construct_tree,
    analyze_heuristics,
    lazy_provide_config,
    search_node,
    search_h_node,
)
from ..lexers import IOSLexer

import sys
import re


if TYPE_CHECKING:
    from typing import Optional
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Generator, Iterable
    else:
        from typing import Generator, Iterable

    from ..responses import Response
    from ..parsers.ios import (
        Root,
        Node,
    )


class IOSContext(Context):
    __slots__ = (
        '__tree',
        '__cursor',
        '__virtual_cursor',
        '__virtual_h_cursor',
        '__is_heuristics',
        '__is_crop',
        '__is_promisc',
    )
    __store: list[IOSContext] = []
    lexer: IOSLexer = IOSLexer

    @property
    def prompt(self) -> str:
        if self.__cursor.name == 'root':
            return ''
        else:
            return self.__cursor.path

    @property
    def tree(self) -> Root:
        return self.__tree

    @property
    def nos_type(self) -> str:
        return 'IOS'

    def __init__(self, name: str, content: list[str], encoding: str = 'utf-8-sig') -> None:
        super().__init__(name, content, encoding)
        self.__is_heuristics = False
        self.__is_crop = False
        self.__is_promisc = False
        self.__tree: Root = construct_tree(self.content, self.delimiter)
        if not self.__tree:
            raise Exception('IOS. Impossible to build a tree.')
        self.__store.append(self)
        self.__cursor: Root | Node = self.__tree
        self.__virtual_cursor: Root | Node = self.__tree
        self.__virtual_h_cursor: Root | Node = self.__tree
        self.spaces = 1
        if 'end' not in self.keywords['top']:
            self.keywords['top'].append('end')
        if 'exit' not in self.keywords['up']:
            self.keywords['up'].append('exit')
        if 'include' not in self.keywords['filter']:
            self.keywords['filter'].append('include')

    def __rebuild_tree(self) -> None:
        self.command_top()
        self.__tree = construct_tree(
            config=self.content,
            delimiter=self.delimiter,
            is_heuristics=self.__is_heuristics,
            is_crop=self.__is_crop,
            is_promisc=self.__is_promisc
        )

    def __get_node_content(self, node: Root | Node) -> Generator[str, None, None]:
        return lazy_provide_config(self.content, node, self.spaces)

    def __prepand_nop(self, data: Iterable[str]) -> Generator[str, None, None]:
        '''
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by __process_fabric method or __mod methods. Final stream does not contain it.
        '''
        yield '\n'
        yield from data

    def __inspect_children(
        self,
        node: Root | Node,
        parent_path: str,
        *,
        is_pair: bool = False
    ) -> Generator[str | tuple[str, Node], None, None]:
        for child in node.children:
            if child.is_accessible:
                path = child.path.replace(parent_path, '').replace(self.delimiter, ' ').strip()
                if is_pair:
                    yield path, child
                else:
                    yield path
            else:
                yield from self.__inspect_children(child, parent_path, is_pair=is_pair)

    def __update_virtual_cursor(self, parts: list[str], *, is_heuristics: bool = False) -> Generator[str, None, None]:
        target: list[Node] = []
        if is_heuristics:
            target = self.__virtual_h_cursor.heuristics
        else:
            target = self.__virtual_cursor.children
        for child in target:
            # We ignore `is_accessible` flag because the virtual cursors are actually virtual.
            if child.name == parts[0]:
                if is_heuristics:
                    self.__virtual_h_cursor = child
                else:
                    self.__virtual_cursor = child
                if parts[1:]:
                    yield from self.__update_virtual_cursor(parts[1:], is_heuristics=is_heuristics)
                else:
                    yield child.name
                break
        else:
            # a child wasn't found
            # so we try to get all matches instead
            yield from filter(lambda x: re.search(rf'^{parts[0]}', x, re.I), map(lambda x: x.name, target))

    def free(self) -> None:
        self.__store.remove(self)
        super().free()

    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        '''
        This method receives a value from user's input symbol by symbol
            and tries to guess the next possible path(s) for this input.
        '''
        if not value:
            return
        parts: list[str] = value.split()
        command: str = parts[0]  # command must be top, show, or go
        sub_command: str = ''
        offset: int = 0
        if command in self.keywords['top']:
            if len(parts) < 3:
                return
            sub_command = parts[1]  # sub_command must be show or go
            if sub_command in self.keywords['show'] or sub_command in self.keywords['go']:
                self.__virtual_cursor = self.__tree
                self.__virtual_h_cursor = self.__tree
                offset = 2
                command = sub_command
            else:
                return
        elif command in self.keywords['show'] or command in self.keywords['go']:
            if len(parts) < 2:
                return
            self.__virtual_cursor = self.__cursor
            self.__virtual_h_cursor = self.__cursor
            offset = 1
        else:
            return
        if self.__is_heuristics and command not in self.keywords['go']:
            yield from chain(
                self.__update_virtual_cursor(copy(parts[offset:]), is_heuristics=False),
                self.__update_virtual_cursor(copy(parts[offset:]), is_heuristics=True)
            )
        else:
            yield from self.__update_virtual_cursor(parts[offset:], is_heuristics=False)

    def get_virtual_from(self, value: str) -> str:
        '''
        This method receives a value from user's input after a Tab's strike and returns
            a word that should be replaced in the input.
        '''
        if not value:
            return ''
        parts: list[str] = value.split()
        command = parts[0]
        if command in self.keywords['top']:
            if len(parts) < 3:
                return ''
            parts = parts[2:]
        elif command in self.keywords['show'] or command in self.keywords['go']:
            if len(parts) < 2:
                return ''
            parts = parts[1:]
        else:
            return ''
        return parts[-1].strip()

    def mod_stubs(self, jump_node: Optional[Node] = None) -> Generator[str | FabricException, None, None]:
        node = self.__cursor if not jump_node else jump_node
        if not node.stubs:
            yield FabricException('No stubs at this level.')
        yield '\n'  # nop
        yield from node.stubs

    def mod_sections(self, jump_node: Optional[Node] = None) -> Generator[str | FabricException, None, None]:
        node = self.__cursor if not jump_node else jump_node
        if not node.children:
            yield FabricException('No sections at this level.')
        yield '\n'
        yield from self.__inspect_children(node, node.path)

    def mod_wildcard(self, data: Iterable[str], args: list[str]) -> Generator[str | FabricException, None, None]:
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
                    if not self.__cursor.children:
                        yield FabricException('No sections at this level.')
                    yield '\n'
                    for path, child in self.__inspect_children(self.__cursor, self.__cursor.path, is_pair=True):
                        if re.search(regexp, path):
                            yield from self.__get_node_content(child)
            except StopIteration:
                yield FabricException

    def mod_diff(
        self,
        args: list[str],
        jump_node: Optional[Node] = None
    ) -> Generator[str | FabricException, None, None]:
        if len(args) != 1:
            yield FabricException('There must be one argument for "diff".')
        if not self.name:
            yield FabricException('Please use "set name" to name this context first.')
        if len(self.__store) <= 1:
            yield FabricException('No other contexts.')
        context_name = args[0]
        if self.name == context_name:
            yield FabricException('You can\'t compare the same context.')
        remote_context: IOSContext = None
        for elem in self.__store:
            if elem.name == context_name:
                remote_context = elem
                break
        else:
            yield FabricException('Remote context has not been found.')
        target: Root | Node = None
        peer: Root | Node = None
        if jump_node:
            target = jump_node
            path = deque(jump_node.path.split(self.delimiter))
            peer = search_node(path, remote_context.tree)
        else:
            target = self.__cursor
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
            list(lazy_provide_config(remote_context.content, peer, remote_context.spaces))
        )

    def __process_fabric(
        self,
        data: Iterable[str],
        mods: list[list[str]],
        *,
        jump_node: Optional[Node] = None
    ) -> Response:

        def __check_leading_mod(name: str, position: int, args_count: int, args_limit: int = 0) -> None:
            if position:
                raise FabricException(f'Incorrect position of "{name}".')
            if args_count != args_limit:
                raise FabricException(f'Incorrect number of arguments for "{name}". Must be {args_limit}.')
        data = self.__prepand_nop(data)
        try:
            for number, elem in enumerate(mods):
                command = elem[0]
                if command in self.keywords['filter']:
                    data = self.mod_filter(data, elem[1:])
                elif command in self.keywords['stubs']:
                    __check_leading_mod(command, number, len(elem[1:]))
                    data = self.mod_stubs(jump_node)
                elif command in self.keywords['sections']:
                    __check_leading_mod(command, number, len(elem[1:]))
                    data = self.mod_sections(jump_node)
                elif command in self.keywords['save']:
                    data = self.mod_save(data, elem[1:])
                    break
                elif command in self.keywords['count']:
                    data = self.mod_count(data, elem[1:])
                    break
                elif command in self.keywords['wildcard']:
                    data = self.mod_wildcard(data, elem[1:])
                elif command in self.keywords['diff']:
                    __check_leading_mod(command, number, len(elem[1:]), 1)
                    data = self.mod_diff(elem[1:], jump_node)
                else:
                    raise FabricException(f'Unknown modificator "{command}".')
            head = next(data)
            if isinstance(head, Exception):
                raise head
            return ContextResponse.success(data)
        except (AttributeError, IndexError) as err:
            return AlertResponse.error(f'Unknown error from the fabric #001: {err}')
        except FabricException as err:
            return AlertResponse.error(f'{err}')
        except StopIteration:
            return AlertResponse.error('Unknown error from the fabric #002.')

    def command_show(self, args: deque[str] = [], mods: list[list[str]] = []) -> Response:
        if args:
            first_arg = args[0]
            if first_arg in self.keywords['version']:
                if len(args) > 1:
                    return AlertResponse.error('Too many arguments for "version".')
                if self.__tree.version:
                    return ContextResponse.success(self.__tree.version)
                return AlertResponse.error('No version has been found.')
            else:
                hpath = copy(args)
                if node := search_node(args, self.__cursor):
                    if mods:
                        return self.__process_fabric(self.__get_node_content(node), mods, jump_node=node)
                    else:
                        return ContextResponse.success(self.__get_node_content(node))
                else:
                    if self.__is_heuristics:
                        if hnode := search_h_node(hpath, self.__cursor):
                            return ContextResponse.success(hnode.stubs)
                    return AlertResponse.error('This path is not correct.')
        else:
            if mods:
                return self.__process_fabric(self.__get_node_content(self.__cursor), mods)
            else:
                return ContextResponse.success(self.__get_node_content(self.__cursor))

    def command_go(self, args: deque[str]) -> Response:
        if not args:
            return AlertResponse.error('Not enough arguments for "go".')
        if node := search_node(args, self.__cursor):
            self.__cursor = node
            return AlertResponse.success()
        return AlertResponse.error('This path is not correct.')

    def command_top(self, args: deque[str] = [], mods: list[list[str]] = []) -> Response:
        if args:
            sub_command = args.popleft()
            temp = self.__cursor
            self.__cursor = self.__tree
            if sub_command in self.keywords['show']:
                result = self.command_show(args, mods)
                self.__cursor = temp
                return result
            elif sub_command in self.keywords['go']:
                result = self.command_go(args)
                if not result.is_ok:
                    self.__cursor = temp
                    return AlertResponse.error(result.value)
                return AlertResponse.success()
            else:
                self.__cursor = temp
                return AlertResponse.error(f'Incorrect sub-command for "top": {sub_command}.')
        else:
            self.__cursor = self.__tree
            return AlertResponse.success()

    def command_up(self, args: deque[str]) -> Response:
        steps: int = 1
        if args:
            if len(args) != 1:
                return AlertResponse.error('There must be one argument for "up".')
            arg = args.popleft()
            if arg in self.keywords['show']:
                if self.__cursor.name == 'root':
                    return AlertResponse.error('You can\'t do a negative lookahead from the top.')
                temp = self.__cursor
                self.__cursor = self.__cursor.parent
                result = self.command_show()
                self.__cursor = temp
                return result
            elif arg.isdigit():
                steps = min(int(arg), UP_LIMIT)
            else:
                return AlertResponse.error(f'Incorrect argument for "up": {arg}.')
        if self.__cursor.name == 'root':
            return AlertResponse.success()
        current = self.__cursor
        while steps:
            if current.name == 'root':
                break
            current = current.parent
            steps -= 1
        self.__cursor = current
        return AlertResponse.success()

    def command_set(self, args: deque[str]) -> Response:
        if not args:
            return AlertResponse.error('Not enough arguments for "set".')
        command = args.popleft()
        if command in ('heuristics', 'crop', 'promisc',):
            if len(args) != 1:
                return AlertResponse.error(f'There must be one argument for "set {command}".')
            value = args.pop()
            value = value.lower()
            if value not in ('on', 'off', '0', '1', 0, 1):
                return AlertResponse.error(f'Unknown argument for "set {command}": {value}. Use: 0, 1, off, on.')
            if command == 'heuristics':
                if value in ('on', '1', 1):
                    if self.__is_heuristics:
                        return AlertResponse.error('The heuristics mode is already active.')
                    self.__is_heuristics = True
                    analyze_heuristics(self.__tree, self.delimiter, self.__is_crop)
                else:
                    self.__is_heuristics = False
            elif command == 'crop':
                if not self.__is_heuristics:
                    return AlertResponse.error('The heuristics mode must be enabled first.')
                if value in ('on', '1', 1):
                    self.__is_crop = True
                else:
                    self.__is_crop = False
                self.__rebuild_tree()
                analyze_heuristics(self.__tree, self.delimiter, self.__is_crop)
            elif command == 'promisc':
                if value in ('on', '1', 1):
                    self.__is_promisc = True
                else:
                    self.__is_promisc = False
                self.__rebuild_tree()
                if self.__is_heuristics:
                    analyze_heuristics(self.__tree, self.delimiter, self.__is_crop)
            return AlertResponse.success(f'The "set {command}" was successfully modified.')
        else:
            args.appendleft(command)
            return super().command_set(args)
