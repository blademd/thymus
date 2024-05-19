from __future__ import annotations

import re

from typing import Optional, cast
from collections.abc import Iterator, Iterable
from collections import deque

from thymus_ast import junos_ng as junos  # type: ignore

from thymus.contexts import Context, FabricException
from thymus.lexers import JunosLexer
from thymus.responses import Response
from thymus.utils import find_common, dot_notation_fix


class JunosContext(Context):
    __slots__ = (
        '_tree',
        '_cursor',
        '_virtual_cursor',
    )
    __store: list[JunosContext] = []

    lexer = JunosLexer

    @property
    def tree(self) -> junos.Root:
        return self._tree

    @property
    def cursor(self) -> junos.Root | junos.Node:
        return self._cursor

    @property
    def path(self) -> str:
        return self._cursor.path

    @property
    def path_offset(self) -> tuple[int, int]:
        if type(self._cursor) is junos.Root:
            return self._cursor.begin, self._cursor.end + 1
        else:
            return self._cursor.begin + 1, self._cursor.end

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
        self.__store.append(self)

    def release(self) -> None:
        if self in self.__store:
            self.__store.remove(self)
        super().release()

    def build(self) -> None:
        tree = junos.construct_tree(self._content, delimiter=self.delimiter)
        if not tree:
            raise Exception('Context was not built.')

        self._tree = tree
        self._cursor: junos.Root | junos.Node = tree
        self._virtual_cursor: junos.Root | junos.Node = tree

    # PRIVATE METHODS

    def _update_virtual_cursor(self, parts: deque[str]) -> Iterator[str]:
        def get_heads(node: junos.Root | junos.Node, comp: str) -> Iterator[str]:
            for child in node.children:
                name = child.name.lower()
                if name.startswith('inactive: '):
                    name = name.replace('inactive: ', '')

                if name.startswith('protect: '):
                    name = name.replace('protect: ', '')
                name = name.strip()

                if name.startswith(comp):
                    yield child.name

        if not parts or not self._virtual_cursor.children:
            return

        head = parts.popleft()
        if head == '|':
            # enlist all possible sections
            yield from map(lambda x: x.name, self._virtual_cursor.children)
            return

        for child in self._virtual_cursor.children:
            name = child.name.lower()
            if name.startswith('inactive: '):
                name = name.replace('inactive: ', '')

            if name.startswith('protect: '):
                name = name.replace('protect: ', '')
            name = name.strip()

            if name == head:
                self._virtual_cursor = child
                if not parts:
                    # nothing left to check in the path
                    # return all encounters
                    yield from get_heads(child.parent, head)
                else:
                    yield from self._update_virtual_cursor(parts)

                return  # we have found all encounters at this stage and can leave
        # no encounters have been found
        if parts:
            # let's see if we can find a doubled match
            extra = parts.popleft()
            parts.appendleft(head + ' ' + extra)
            yield from self._update_virtual_cursor(parts)
        else:
            # showing all sections that names start with the head
            yield from get_heads(self._virtual_cursor, head)

    def _prepand_nop(self, data: Iterable[str]) -> Iterator[str | FabricException]:
        """
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by _process_fabric method or _mod_* methods. Final stream does not contain it.
        It also casts Iterable[str] to Iterator[str | FabricException] despite there is no exceptions in the stream.
        """
        yield '\n'
        yield from data

    def _process_fabric(  # TODO: should be rewritten later
        self, data: Iterable[str], mods: list[list[str]], *, jump_node: Optional[junos.Node] = None
    ) -> Response:
        def check_leading_mod(name: str, position: int, args_count: int, args_limit=0, skip=False) -> None:
            if position:
                raise FabricException(f'Incorrect position of "{name}".')

            if args_count != args_limit and not skip:
                raise FabricException(f'Incorrect number of arguments for "{name}". Must be {args_limit}.')

        flat_output = True
        modified_data = self._prepand_nop(data)

        try:
            for number, element in enumerate(mods):
                command = element[0]

                # Filter
                if command == self.alias_sub_command_filter:
                    modified_data = self.mod_filter(modified_data, element[1:])
                    flat_output = True
                # Wildcard
                elif command == self.alias_sub_command_wildcard:
                    modified_data = self.mod_wildcard(modified_data, element[1:])
                    flat_output = False
                # Save
                elif command == self.alias_sub_command_save:
                    modified_data = cast('Iterator[str]', modified_data)
                    modified_data = junos.lazy_provide_config(
                        modified_data, block=' ' * self.spaces, hide_secrets=False
                    )
                    modified_data = self.mod_save(modified_data, element[1:])
                    break
                # Count
                elif command == self.alias_sub_command_count:
                    modified_data = self.mod_count(modified_data, element[1:])
                    break
                # Diff
                elif command == self.alias_sub_command_diff:
                    check_leading_mod(command, number, len(element[1:]), skip=True)
                    modified_data = self.mod_diff(element[1:], jump_node)
                    flat_output = False
                # Inactive
                elif command == self.alias_sub_command_inactive:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = self.mod_inactive(jump_node)
                    flat_output = False
                # Stubs
                elif command == self.alias_sub_command_stubs:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = self.mod_stubs(jump_node)
                # Sections
                elif command == self.alias_sub_command_sections:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = self.mod_sections(jump_node)
                # Contains
                elif command == self.alias_sub_command_contains:
                    check_leading_mod(command, number, len(element[1:]), 1)
                    modified_data = self.mod_contains(element[1:], jump_node)
                # Reveal
                elif command == self.alias_sub_command_reveal:
                    check_leading_mod(command, number, len(element[1:]))
                    modified_data = cast('Iterator[str]', modified_data)
                    modified_data = junos.lazy_provide_config(
                        modified_data, block=' ' * self.spaces, hide_secrets=False
                    )
                else:
                    raise FabricException(f'Unknown sub-command: "{command}".')

            head = next(modified_data)

            if isinstance(head, Exception):
                raise head

            modified_data = cast('Iterator[str]', modified_data)

            if flat_output:
                return Response.success(modified_data)
            else:
                return Response.success(junos.lazy_provide_config(modified_data, block=' ' * self._spaces))

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
                if node := junos.search_node(args, self._cursor):
                    data = self._content[node.begin + 1 : node.end]

                    if mods:
                        return self._process_fabric(data, mods, jump_node=node)

                    return Response.success(junos.lazy_provide_config(data, block=' ' * self._spaces))

                return Response.error('This path is incorrect.')
        else:
            if type(self._cursor) is junos.Root:
                # Here we show all the content
                data = self._content[self._cursor.begin : self._cursor.end + 1]
            else:
                # Here we skip the first line (with a section name) and the last too (with the "}")
                data = self._content[self._cursor.begin + 1 : self._cursor.end]

            if mods:
                return self._process_fabric(data, mods)
            else:
                return Response.success(junos.lazy_provide_config(data, block=' ' * self._spaces))

    def command_go(self, args: deque[str]) -> Response:
        if not args:
            return Response.error(f'Not enough arguments for "{self.alias_command_go}".')

        if node := junos.search_node(args, self._cursor):
            self._cursor = node
            return Response.success()

        return Response.error('This path is incorrect.')

    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
        if args:
            sub_command = args.popleft()

            temp_cursor = self._cursor
            self._cursor = self._tree

            if sub_command == self.alias_command_show:
                result = self.command_show(args, mods)
                self._cursor = temp_cursor
                return result
            elif sub_command == self.alias_command_go:
                if (result := self.command_go(args)).status == 'error':
                    self._cursor = temp_cursor
                    return Response.error(result.value)
            else:
                self._cursor = temp_cursor
                return Response.error(f'Incorrect sub-command for "{self.alias_command_top}": {sub_command}.')
        else:
            self._cursor = self._tree

        return Response.success()

    def command_up(self, args: deque[str], mods: list[list[str]]) -> Response:
        steps = 1

        if args:
            arg = args.popleft()

            if arg == self.alias_command_show:
                if type(self._cursor) is junos.Root:
                    return Response.error("You can't do a negative lookahead from the top.")

                temp = self._cursor
                assert type(self._cursor) is junos.Node
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

        if type(self._cursor) is junos.Root:
            return Response.success()

        current = self._cursor

        while steps:
            if type(current) is junos.Root:
                break

            assert type(current) is junos.Node
            current = current.parent
            steps -= 1

        self._cursor = current

        return Response.success()

    # MODS

    def mod_wildcard(self, data: Iterator[str | FabricException], args: list[str]) -> Iterator[str | FabricException]:
        if not data or len(args) != 1:
            yield FabricException(f'Incorrect arguments for "{self.alias_sub_command_wildcard}".')

        try:
            re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "{self.alias_sub_command_wildcard}": {args[0]}.')
        else:
            try:
                head = next(data)

                if isinstance(head, Exception):
                    yield head
                else:
                    yield '\n'
                    data = cast('Iterator[str]', data)
                    yield from junos.lazy_wildcard_parser(data, path='', pattern=args[0], delimiter=self.delimiter)
            except StopIteration:
                yield FabricException()

    def mod_diff(self, args: list[str], jump_node: Optional[junos.Node] = None) -> Iterator[str | FabricException]:
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
            context_name = args[0]

            if not self.name:
                yield FabricException('Please use "set name" to name this context first.')

            if self.name == context_name:
                yield FabricException("You can't compare the same context.")

            for elem in self.__store:
                if elem.name == context_name:
                    remote_context = elem
                    break
            else:
                yield FabricException('Remote context has not been found.')

        target: junos.Root | junos.Node = self._cursor

        if jump_node:
            target = jump_node

        if target.name == 'root':
            peer = remote_context.tree

            if compared := junos.compare_nodes(target, peer):
                yield '\n'
                yield from junos.lazy_provide_compare(compared)
            else:
                yield FabricException('Fail to compare the contexts. The same content?')
        else:
            path = junos.make_path(target.path, delimiter=self.delimiter)

            if peer := junos.search_node(path, remote_context.tree):
                if compared := junos.compare_nodes(target, peer):
                    yield '\n'
                    yield from junos.lazy_provide_compare(compared)
                else:
                    yield FabricException('Fail to compare the contexts. The same content?')
            else:
                yield FabricException('Comparing context lacks this path.')

    def mod_inactive(self, jump_node: Optional[junos.Node] = None) -> Iterator[str | FabricException]:
        node = jump_node if jump_node else self._cursor

        if tree := junos.search_inactives(node):
            yield '\n'
            yield from junos.lazy_provide_inactives(tree)
        else:
            yield FabricException('No inactives were found.')

    def mod_stubs(self, jump_node: Optional[junos.Node] = None) -> Iterator[str | FabricException]:
        node = jump_node if jump_node else self._cursor

        if not node.stubs:
            yield FabricException('No stubs at this level.')

        yield '\n'
        yield from node.stubs

    def mod_sections(self, jump_node: Optional[junos.Node] = None) -> Iterator[str | FabricException]:
        node = jump_node if jump_node else self._cursor
        if not node.children:
            yield FabricException('No sections ath this level.')

        yield '\n'
        yield from map(lambda section: section.name, node.children)

    def mod_contains(self, args: list[str], jump_node: Optional[junos.Node] = None) -> Iterator[str | FabricException]:
        def replace_path(source: str, path: str) -> str:
            return source.replace(path, '').replace(self.delimiter, ' ').strip()

        def lookup_child(node: junos.Root | junos.Node, path: str) -> Iterator[str]:
            for child in node.children:
                yield from lookup_child(child, path)

            if re.search(args[0], node.name):
                yield replace_path(node.path, path)

            for stub in filter(lambda stub: re.search(args[0], stub), node.stubs):
                yield f'{replace_path(node.path, path)}: "{stub}"'

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
        node: Optional[junos.Root | junos.Node] = None

        if virtual_path:
            modified_path = junos.make_path(virtual_path, delimiter=self.delimiter)
            node = junos.search_node(modified_path, self._tree)

            if not node:
                virtual_path = virtual_path.replace(self.delimiter, ' ')
                raise ValueError(f'Node for path "{virtual_path}" is not found.')

            return node.begin + 1, node.end, self._content[node.begin + 1 : node.end]
        else:
            node = self._tree
            return node.begin, node.end + 1, self._content[node.begin : node.end + 1]

    def get_possible_sections(self, value: str) -> Iterator[str]:
        if not value:
            return

        value = dot_notation_fix(value)
        parts = value.split()

        if parts[0] == self.alias_command_top:
            if len(parts) > 2 and (parts[1] == self.alias_command_show or parts[1] == self.alias_command_go):
                self._virtual_cursor = self.tree
                yield from self._update_virtual_cursor(deque(parts[2:]))
        elif parts[0] == self.alias_command_up:
            if len(parts) > 2 and (parts[1] == self.alias_command_show or parts[1] == self.alias_command_go):
                if type(self._cursor) is junos.Node:
                    self._virtual_cursor = self._cursor.parent
                yield from self._update_virtual_cursor(deque(parts[2:]))
        elif parts[0] == self.alias_command_show or parts[0] == self.alias_command_go:
            if len(parts) > 1:
                self._virtual_cursor = self._cursor
                yield from self._update_virtual_cursor(deque(parts[1:]))
        else:
            yield from self.get_possible_commands(value)

    def get_virtual_from(self, value: str) -> str:
        if not value:
            return ''

        value = dot_notation_fix(value)
        parts = value.split()

        if len(parts) == 1:
            return value

        first = ''

        if parts[0] == self.alias_command_top or parts[0] == self.alias_command_up:
            if len(parts) < 3:
                return ''

            first = parts[0]
            parts = parts[1:]

        if parts[0] != self.alias_command_show and parts[0] != self.alias_command_go:
            return ''

        new_value = ' '.join(parts[1:])

        if self._virtual_cursor.name == 'root':
            return new_value

        path = self._virtual_cursor.path
        path = path.replace('inactive: ', '')
        path = path.replace('protect: ', '')
        rpath = self._cursor.path

        if not first and self._cursor.name != 'root':
            path = path.replace(self._cursor.path, '', 1)

        spath = path.replace(self.delimiter, ' ')
        spath = spath.strip().lower()

        if first == self.alias_command_up:
            if path.startswith(rpath):
                # when user tries to do `up show x y`
                # and the user is in `x` already
                xparts = spath.split()

                for index, xpart in enumerate(xparts):
                    if new_value.startswith(xpart):
                        break

                return new_value.replace(' '.join(xparts[index:]), '', 1)
            else:
                common = find_common([path, rpath])
                common = common.replace(self.delimiter, ' ')
                common = common.strip()

                xpath = path.replace(common, '', 1)
                xpath = xpath.replace(self.delimiter, ' ')
                xpath = xpath.strip()

                if new_value.startswith(xpath):
                    return new_value.replace(xpath, '', 1)
        else:
            if new_value.startswith(spath):
                return new_value.replace(spath, '', 1)

        return new_value

    # STATICMETHODS

    @staticmethod
    def validate_commit(commit_data: Iterable[str]) -> None:
        """Method validates the commit data checking whether the last bracket is closed. Also, it checks if
        there are any duplicate sections or stubs.
        """

        def walk(node: junos.Root | junos.Node) -> None:
            names = []
            for child in node.children:
                names.append(child.name)
                walk(child)

            if len(set(names)) != len(node.children):
                raise Exception('Duplicate sections.')

            if len(set(node.stubs)) != len(node.stubs):
                raise Exception('Duplicate stubs.')

        tree = junos.construct_tree(commit_data)
        if not tree:
            raise ValueError('Nothing to commit, cannot generate a tree.')

        if tree.children and not tree.children[-1].is_closed:
            raise ValueError('Unclosed section is present.')

        try:
            walk(tree)
        except Exception as error:
            raise ValueError(error)
