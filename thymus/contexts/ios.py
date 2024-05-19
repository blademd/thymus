from __future__ import annotations

import re

from typing import Optional
from collections.abc import Iterator, Iterable
from collections import deque
from copy import copy
from itertools import chain

from thymus_ast import ios  # type: ignore

from thymus.contexts import Context, FabricException
from thymus.lexers import IOSLexer
from thymus.responses import Response
from thymus.utils import find_common


class IOSContext(Context):
    __slots__ = (
        '_tree',
        '_cursor',
        '_virtual_cursor',
        '_virtual_h_cursor',
        '_heuristics',
        '_base_heuristics',
        '_crop',
        '_promisc',
        '_find_head',
    )
    __store: list[IOSContext] = []

    lexer = IOSLexer

    # READ-ONLY PROPERTIES

    @property
    def tree(self) -> ios.Root:
        return self._tree

    @property
    def cursor(self) -> ios.Root | ios.Node:
        return self._cursor

    @property
    def path(self) -> str:
        return self._cursor.path

    @property
    def path_offset(self) -> tuple[int, int]:
        return self._cursor.begin, self._cursor.end

    # CONFIGURABLE PROPERTIES

    @property
    def heuristics(self) -> bool:
        self._heuristics: bool
        return self._heuristics

    @heuristics.setter
    def heuristics(self, value: bool | str) -> None:
        if type(value) is not bool:
            if type(value) is str:
                if value in ('0', 'off'):
                    value = False
                elif value in ('1', 'on'):
                    value = True
                else:
                    raise ValueError(f'Incorrect value for "heuristics": {value}.')
            else:
                raise TypeError(f'Incorrect type for "heuristics": {type(value)}.')

        if self.is_built:
            self._heuristics = value
            self.build()

        self._heuristics = value

    @property
    def base_heuristics(self) -> bool:
        self._base_heuristics: bool
        return self._base_heuristics

    @base_heuristics.setter
    def base_heuristics(self, value: bool | str) -> None:
        if type(value) is not bool:
            if type(value) is str:
                if value in ('0', 'off'):
                    value = False
                elif value in ('1', 'on'):
                    value = True
                else:
                    raise ValueError(f'Incorrect value for "base_heuristics": {value}.')
            else:
                raise TypeError(f'Incorrect type for "base_heuristics": {type(value)}.')

        if self.is_built:
            self._base_heuristics = value
            self.build()

        self._base_heuristics = value

    @property
    def crop(self) -> bool:
        self._crop: bool
        return self._crop

    @crop.setter
    def crop(self, value: bool | str) -> None:
        if type(value) is not bool:
            if type(value) is str:
                if value in ('0', 'off'):
                    value = False
                elif value in ('1', 'on'):
                    value = True
                else:
                    raise ValueError(f'Incorrect value for "crop": {value}.')
            else:
                raise TypeError(f'Incorrect type for "crop": {type(value)}.')

        if self.is_built:
            if not self._heuristics:
                raise ValueError('The heuristics mode must be enabled first.')

            self._crop = value
            self.build()

        self._crop = value

    @property
    def promisc(self) -> bool:
        self._promisc: bool
        return self._promisc

    @promisc.setter
    def promisc(self, value: bool | str) -> None:
        if type(value) is not bool:
            if type(value) is str:
                if value in ('0', 'off'):
                    value = False
                elif value in ('1', 'on'):
                    value = True
                else:
                    raise ValueError(f'Incorrect value for "promisc": {value}.')
            else:
                raise TypeError(f'Incorrect type for "promisc": {type(value)}.')

        if self.is_built:
            self._promisc = value
            self.build()

        self._promisc = value

    @property
    def find_head(self) -> bool:
        self._find_head: bool
        return self._find_head

    @find_head.setter
    def find_head(self, value: bool | str) -> None:
        if type(value) is not bool:
            if type(value) is str:
                if value in ('0', 'off'):
                    value = False
                elif value in ('1', 'on'):
                    value = True
                else:
                    raise ValueError(f'Incorrect value for "find_head": {value}.')
            else:
                raise TypeError(f'Incorrect type for "find_head": {type(value)}.')

        if self.is_built:
            if not self._promisc:
                raise ValueError('The promisc mode must be enabled first.')

            self._find_head = value
            self.build()

        self._find_head = value

    def __init__(
        self,
        context_id: int,
        name: str,
        content: list[str],
        encoding: str,
        neighbors: list[Context],
        saves_dir: str,
    ) -> None:
        super().__init__(context_id, name, content, encoding, neighbors, saves_dir)
        self._base_heuristics = True
        self._heuristics = False
        self._crop = False
        self._promisc = False
        self._find_head = False
        self.__store.append(self)

    def release(self) -> None:
        if self in self.__store:
            self.__store.remove(self)
        return super().release()

    def build(self) -> None:
        settings = ios.TreeSettings(
            heuristics=self._heuristics,
            base_heuristics=self._base_heuristics,
            crop=self._crop,
            promisc=self._promisc,
            delimiter=self.delimiter,
            find_head=self._find_head,
        )
        tree = ios.construct_tree_second(self._content, settings=settings)

        if not tree:
            raise Exception('Context was not built.')

        self._tree = tree
        self._cursor: ios.Root | ios.Node = tree
        self._virtual_cursor: ios.Root | ios.Node = tree
        self._virtual_h_cursor: ios.Root | ios.Node = tree

    # PRIVATE METHODS

    def _update_virtual_cursor(self, parts: deque[str], *, heuristics=False) -> Iterator[str]:
        # heuristics here is a marker that spots which cursor and its nodes to use
        if not parts:
            return

        target = self._virtual_h_cursor.heuristics if heuristics else self._virtual_cursor.children
        head = parts.popleft()
        head = head.lower()

        if head == '|':
            yield from map(lambda node: node.name, target)

        for child in target:
            # We ignore `is_accessible` flag because the virtual cursors are actually virtual.
            if child.name.lower() == head:
                if heuristics:
                    self._virtual_h_cursor = child
                else:
                    self._virtual_cursor = child

                if parts:
                    yield from self._update_virtual_cursor(parts, heuristics=heuristics)
                else:
                    yield from filter(lambda name: name.lower().startswith(head), map(lambda node: node.name, target))

                return

        # no child found
        # so, try to get all matched then
        yield from filter(lambda name: name.lower().startswith(head), map(lambda node: node.name, target))

    def _inspect_children_path(self, node: ios.Root | ios.Node, parent_path: str) -> Iterator[str]:
        for child in node.children:
            if child.is_accessible:
                yield child.path.replace(parent_path, '').replace(self.delimiter, ' ').strip()
            else:
                yield from self._inspect_children_path(child, parent_path)

    def _inspect_children_pair(self, node: ios.Root | ios.Node, parent_path: str) -> Iterator[tuple[str, ios.Node]]:
        for child in node.children:
            if child.is_accessible:
                path = child.path.replace(parent_path, '').replace(self.delimiter, ' ').strip()
                yield path, child
            else:
                yield from self._inspect_children_pair(child, parent_path)

    def _prepand_nop(self, data: Iterable[str]) -> Iterator[str | FabricException]:
        """
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by _process_fabric method or _mod_* methods. Final stream does not contain it.
        It also casts Iterable[str] to Iterator[str | FabricException] despite there is no exceptions in the stream.
        """
        yield '\n'
        yield from data

    def _process_fabric(
        self, data: Iterable[str], mods: list[list[str]], *, jump_node: Optional[ios.Node] = None
    ) -> Response:
        def check_leading_mod(name: str, position: int, args_count: int, args_limit=0, skip=False) -> None:
            if position:
                raise FabricException(f'Incorrect position of "{name}".')

            if args_count != args_limit and not skip:
                raise FabricException(f'Incorrect number of arguments for "{name}". Must be {args_limit}.')

        modified_data = self._prepand_nop(data)

        try:
            for number, element in enumerate(mods):
                command = element[0]

                # Filter
                if command == self.alias_sub_command_filter:
                    modified_data = self.mod_filter(modified_data, element[1:])
                # Stubs
                elif command == self.alias_sub_command_stubs:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = self.mod_stubs(jump_node)
                # Sections
                elif command == self.alias_sub_command_sections:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = self.mod_sections(jump_node)
                # Save
                elif command == self.alias_sub_command_save:
                    modified_data = self.mod_save(modified_data, element[1:])
                    break
                # Count
                elif command == self.alias_sub_command_count:
                    modified_data = self.mod_count(modified_data, element[1:])
                    break
                # Wildcard
                elif command == self.alias_sub_command_wildcard:
                    modified_data = self.mod_wildcard(modified_data, element[1:], jump_node)
                # Diff
                elif command == self.alias_sub_command_diff:
                    check_leading_mod(command, number, len(element[1:]), skip=True)
                    modified_data = self.mod_diff(element[1:], jump_node)
                # Contains
                elif command == self.alias_sub_command_contains:
                    check_leading_mod(command, number, len(element[1:]), 1)
                    modified_data = self.mod_contains(element[1:], jump_node)
                else:
                    raise FabricException(f'Unknown sub-command: "{command}".')

            head = next(modified_data)

            if isinstance(head, Exception):
                raise head

            return Response.success(modified_data)

        except FabricException as error:
            return Response.error(str(error))

        except (AttributeError, IndexError):
            return Response.error('Unknown error from the fabric #001')

        except StopIteration:
            return Response.error('Unknown error from the fabric #002.')

        except Exception:
            return Response.error('Unknown error from the fabric #003.')

    # COMMANDS

    def command_show(self, args: deque[str], mods: list[list[str]]) -> Response:
        if args:
            if args[0] == 'version':
                if len(args) > 1:
                    return Response.error(f'Too many arguments for "{self.alias_command_show} version".')

                if self._tree.version:
                    return Response.success(self._tree.version)
                else:
                    return Response.error('No version found.')
            else:
                copied_path = copy(args)

                if node := ios.search_node(args, self._cursor):
                    if mods:
                        return self._process_fabric(
                            data=ios.lazy_provide_config(self._content, node, alignment=self._spaces, is_started=True),
                            mods=mods,
                            jump_node=node,
                        )
                    else:
                        return Response.success(
                            ios.lazy_provide_config(self._content, node, alignment=self._spaces, is_started=True)
                        )
                else:
                    if self._heuristics:
                        if h_node := ios.search_h_node(copied_path, self._cursor):
                            return Response.success(h_node.stubs)

                    return Response.error('This path is incorrect.')
        else:
            if mods:
                return self._process_fabric(
                    data=ios.lazy_provide_config(self._content, self._cursor, alignment=self._spaces, is_started=True),
                    mods=mods,
                )
            else:
                return Response.success(
                    ios.lazy_provide_config(self._content, self._cursor, alignment=self._spaces, is_started=True)
                )

    def command_go(self, args: deque[str]) -> Response:
        if not args:
            return Response.error(f'Not enough arguments for "{self.alias_command_go}".')

        if node := ios.search_node(args, self._cursor):
            self._cursor = node
        else:
            return Response.error('This path is incorrect.')

        return Response.success()

    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
        if args:
            sub_command = args.popleft()

            temp = self._cursor

            if sub_command == self.alias_command_show:
                result = self.command_show(args, mods)
                self._cursor = temp
                return result
            elif sub_command == self.alias_command_go:
                if (result := self.command_go(args)).status == 'error':
                    self._cursor = temp
                    return Response.error(result.value)
            else:
                self._cursor = temp
                return Response.error(f'Incorrect sub-command for "{self.alias_command_top}": {sub_command}.')
        else:
            self._cursor = self._tree

        return Response.success()

    def command_up(self, args: deque[str], mods: list[list[str]]) -> Response:
        steps = 1

        if args:
            arg = args.popleft()

            if arg == self.alias_command_show:
                if type(self._cursor) is ios.Root:
                    return Response.error("You can't do a negative lookahead from the top.")

                temp = self._cursor

                assert type(self._cursor) is ios.Node
                self._cursor = self._cursor.parent
                result = self.command_show(args, mods)
                self._cursor = temp
                return result
            elif arg.isdigit():
                if len(args):
                    return Response.error(f'There must be one argument for "{self.alias_command_up}".')

                steps = min(int(arg), self._up_limit)
            else:
                return Response.error(f'Incorrect argument for "{self.alias_command_up}": {arg}.')

        if type(self._cursor) is ios.Root:
            return Response.success()

        current = self._cursor

        while steps:
            if type(current) is ios.Root:
                break

            assert type(current) is ios.Node
            current = current.parent
            if current.is_accessible:
                steps -= 1

        self._cursor = current

        return Response.success()

    # MODS

    def mod_diff(self, args: list[str], jump_node: Optional[ios.Node] = None) -> Iterator[str | FabricException]:
        if not args:
            yield FabricException(f'There must be at least one argument for "{self.alias_sub_command_diff}".')
        elif len(args) > 2:
            yield FabricException(f'Too many arguments for "{self.alias_sub_command_diff}".')
        elif len(args) == 2:
            # Rollback case
            if args[0] != 'rollback':
                yield FabricException(f'Unsupported mode for "{self.alias_sub_command_diff}": {args[0]}.')

            if len(self._neighbors) < 2:
                yield FabricException('Nothing to compare.')

            context_id_str = args[1]
            if not context_id_str.isdigit():
                yield FabricException('Rollback ID must be a numeric value.')

            context_id = int(context_id_str)
            if context_id == self.context_id:
                yield FabricException("You can't compare the same context.")
            elif context_id >= len(self._neighbors):
                yield FabricException(f'Incorrect ID for the target context: {context_id}.')

            remote_context = self._neighbors[context_id]
        else:
            # Regular case
            if not self.name:
                yield FabricException('Please use "set name" to name this context first.')

            if len(self.__store) <= 1:
                yield FabricException('No other contexts.')

            context_name = args[0]

            if self.name == context_name:
                yield FabricException("You can't compare the same context.")

            for element in self.__store:
                if element.name == context_name and type(element) is type(self):
                    remote_context = element
                    break
            else:
                yield FabricException('Remote context has not been found.')

        target: ios.Root | ios.Node = self._cursor

        if jump_node:
            target = jump_node

        if target.name == 'root':
            peer = remote_context.tree
        else:
            peer = ios.search_node(deque(target.path.split(self.delimiter)), remote_context.tree)

        if not peer:
            yield FabricException(f'Remote context lacks this path: {target.path.replace(self.delimiter, " ")}.')

        if compared := ios.compare_nodes(target, peer):
            yield '\n'
            yield from ios.lazy_provide_compare(compared, delimiter=self.delimiter, alignment=self._spaces)
        else:
            yield FabricException('Fail to compare the contexts. The same content?')

    def mod_stubs(self, jump_node: Optional[ios.Node] = None) -> Iterator[str | FabricException]:
        node = jump_node if jump_node else self._cursor

        if not node.stubs:
            yield FabricException('No stubs at this level.')

        yield '\n'
        yield from node.stubs

    def mod_sections(self, jump_node: Optional[ios.Node] = None) -> Iterator[str | FabricException]:
        node = jump_node if jump_node else self._cursor

        if not node.children:
            yield FabricException('No sections at this level.')

        yield '\n'
        yield from self._inspect_children_path(node, node.path)

    def mod_wildcard(
        self, data: Iterator[str | FabricException], args: list[str], jump_node: Optional[ios.Node] = None
    ) -> Iterator[str | FabricException]:
        if not data or len(args) != 1:
            yield FabricException(f'Incorrect arguments for "{self.alias_sub_command_wildcard}".')

        try:
            regexp = re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "{self.alias_sub_command_wildcard}": {args[0]}.')
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
                        if re.search(regexp, path):
                            yield from ios.lazy_provide_config(
                                self._content, child, alignment=self._spaces, is_started=True
                            )
            except StopIteration:
                yield FabricException()

    def mod_contains(self, args: list[str], jump_node: Optional[ios.Node] = None) -> Iterator[str | FabricException]:
        def replace_path(source: str, head: str) -> str:
            return source.replace(head, '').replace(self.delimiter, ' ').strip()

        def lookup_child(node: ios.Root | ios.Node, path: str = '') -> Iterator[str]:
            for child in node.children:
                yield from lookup_child(child, path)

            if not node.is_accessible:
                return

            if re.search(args[0], node.path.replace(self.delimiter, ' ')):
                yield replace_path(node.path, path)

            for stub in filter(lambda x: re.search(args[0], x), node.stubs):
                yield f'{replace_path(node.path, path)}: "{stub}"' if node.path else f'"{stub}"'

        if len(args) != 1:
            yield FabricException(f'There must be one argument for "{self.alias_sub_command_contains}".')

        node = jump_node if jump_node else self._cursor

        if not node.children:
            yield FabricException('No sections at this level.')

        try:
            re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "{self.alias_sub_command_contains}": {args[0]}.')

        yield '\n'
        yield from lookup_child(node, node.path)

    # GETTERS

    def get_rollback_config(self, virtual_path: str) -> tuple[int, int, Iterable[str]]:
        node: Optional[ios.Root | ios.Node] = None

        if virtual_path:
            node = ios.search_node(deque(virtual_path.split(self.delimiter)), self._tree)

            if not node:
                virtual_path = virtual_path.replace(self.delimiter, ' ')
                raise ValueError(f'Node for path "{virtual_path}" is not found.')
        else:
            node = self._tree

        return node.begin, node.end, self._content[node.begin : node.end]

    def get_possible_sections(self, value: str) -> Iterator[str]:
        # This method receives a value from user's input symbol by symbol
        # and tries to guess the next possible path(s) for this input.

        if not value:
            return

        value = value.lower()
        parts = value.split()

        command = parts[0]
        sub_command = ''
        offset = 0

        if command == self.alias_command_top:
            if len(parts) < 3:
                return

            sub_command = parts[1]

            if sub_command == self.alias_command_show or sub_command == self.alias_command_go:
                self._virtual_cursor = self._tree
                self._virtual_h_cursor = self._tree

                offset = 2
                command = sub_command
            else:
                return
        elif command == self.alias_command_up:
            if len(parts) < 3:
                return

            sub_command = parts[1]

            if sub_command == self.alias_command_show or sub_command == self.alias_command_go:
                temp = self._cursor

                self.command_up(deque(), [])
                self._virtual_cursor = self._cursor
                self._virtual_h_cursor = self._cursor

                offset = 2
                command = sub_command

                self._cursor = temp
            else:
                return
        elif command == self.alias_command_show or command == self.alias_command_go:
            if len(parts) < 2:
                return

            self._virtual_cursor = self._cursor
            self._virtual_h_cursor = self._cursor

            offset = 1
        else:
            yield from self.get_possible_commands(value)
            return

        data = deque(parts[offset:])

        if self._heuristics and command != self.alias_command_go:
            yield from chain(
                self._update_virtual_cursor(copy(data)), self._update_virtual_cursor(data, heuristics=True)
            )
        else:
            yield from self._update_virtual_cursor(data)

    def get_virtual_from(self, value: str) -> str:
        # This method receives a value from a user's input after a Tab's strike
        # and returns a word that should be replaced in the input.

        if not value:
            return ''

        first_command = ''
        parts = value.split()

        if len(parts) == 1:
            return value

        command = parts[0]

        if command == self.alias_command_top or command == self.alias_command_up:
            if len(parts) < 3:
                return ''

            first_command = command
            parts = parts[2:]
        elif command == self.alias_command_show or command == self.alias_command_go:
            if len(parts) < 2:
                return ''

            parts = parts[1:]
        else:
            return ''

        modified_input = ' '.join(parts)
        current_path = self._cursor.path.replace(self.delimiter, ' ')
        virtual_path = self._virtual_cursor.path.replace(self.delimiter, ' ')
        virtual_h_path = self._virtual_h_cursor.path.replace(self.delimiter, ' ')

        temp = self._cursor

        if first_command == self.alias_command_up:
            self.command_up(deque(), [])
            current_path = self._cursor.path.replace(self.delimiter, ' ')

        if current_path:
            virtual_path = virtual_path.replace(current_path, '', 1)
            virtual_h_path = virtual_h_path.replace(current_path, '', 1)

        self._cursor = temp

        virtual_path = virtual_path.strip().lower()
        virtual_h_path = virtual_h_path.strip().lower()

        # here we need to find out which virtual path has more in common with the input
        f = find_common([virtual_path, modified_input])
        s = find_common([virtual_h_path, modified_input])

        if len(f) == len(s) or len(f) > len(s):
            return modified_input.replace(f, '', 1)
        else:
            return modified_input.replace(s, '', 1)

    # STATIC METHODS

    @staticmethod
    def validate_commit(commit_data: Iterable[str]) -> None:
        def walk(node: ios.Root | ios.Node) -> None:
            names = []
            for child in node.children:
                names.append(child.name)
                walk(child)

            if len(set(names)) != len(node.children):
                raise Exception('Duplicate sections.')

            if len(set(node.stubs)) != len(node.stubs):
                raise Exception('Duplicate stubs.')

        data = list(commit_data)
        data.insert(0, 'version ')
        data.append('end')

        tree = ios.construct_tree(data)
        if not tree:
            raise ValueError('Nothing to commit, cannot generate a tree.')

        try:
            walk(tree)
        except Exception as error:
            raise ValueError(error)
