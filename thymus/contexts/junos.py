from __future__ import annotations

import sys
import re

from typing import TYPE_CHECKING, Optional
from collections import deque

if sys.version_info.major == 3 and sys.version_info.minor >= 9:
    from collections.abc import Generator, Iterable, Iterator
else:
    from typing import Generator, Iterable, Iterator

from thymus_ast.junos import (  # type: ignore
    Root,
    Node,
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
from ..lexers import JunosLexer
from ..misc import find_common


if TYPE_CHECKING:
    from logging import Logger


class JunOSContext(Context):
    __slots__: tuple[str, ...] = (
        '_tree',
        '_cursor',
        '_virtual_cursor',
    )
    __store: list[JunOSContext] = []
    lexer: type[JunosLexer] = JunosLexer

    @property
    def prompt(self) -> str:
        if self._cursor['name'] == 'root':
            return ''
        else:
            return self._cursor['path']

    @property
    def tree(self) -> Root:
        return self._tree

    @property
    def nos_type(self) -> str:
        return 'JUNOS'

    def __init__(
        self, name: str, content: list[str], *, encoding: str, settings: dict[str, str | int], logger: Logger
    ) -> None:
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)
        self._tree: Root = construct_tree(self.content, self.delimiter)
        if not self._tree or not self._tree.get('children'):
            raise Exception(f'{self.nos_type}. Impossible to build a tree.')
        self.__store.append(self)
        self._cursor: Root | Node = self._tree
        self._virtual_cursor: Root | Node = self._tree
        if 'match' not in self.keywords['filter']:
            self.keywords['filter'].append('match')
        if 'wc_filter' not in self.keywords['wildcard']:
            self.keywords['wildcard'].append('wc_filter')
        if 'compare' not in self.keywords['diff']:
            self.keywords['diff'].append('compare')
        if 'inactive' not in self.keywords:
            self.keywords['inactive'] = ['inactive', 'inactives']

    def free(self) -> None:
        self.__store.remove(self)
        super().free()

    def apply_settings(self, settings: dict[str, str | int]) -> None:
        if hasattr(self, '_tree') and self._tree:
            self.logger.debug('Trying to apply settings with a completed tree.')
            return
        super().apply_settings(settings)

    def _update_virtual_cursor(self, parts: deque[str]) -> Generator[str, None, None]:
        def get_heads(node: Root | Node, comp: str) -> Generator[str, None, None]:
            for child in node['children']:
                name = child['name'].lower()
                if name.startswith('inactive: '):
                    name = name.replace('inactive: ', '')
                if name.startswith(comp):
                    yield child['name']

        if not parts or not self._virtual_cursor['children']:
            return
        head = parts.popleft()
        if head == '|':
            # enlist all possible sections
            yield from map(lambda x: x['name'], self._virtual_cursor['children'])
            return
        for child in self._virtual_cursor['children']:
            name = child['name']
            name = name.lower()
            if name.startswith('inactive: '):
                name = name.replace('inactive: ', '')
            if name == head:
                self._virtual_cursor = child
                if not parts:
                    # nothing left to check in the path
                    # return all encounters
                    yield from get_heads(child['parent'], head)
                else:
                    yield from self._update_virtual_cursor(parts)
                return  # we have found all encounters at this stage and can leave
        # no encounters have been found
        if parts:
            # let's see if we can find a doubled match
            extra = parts.popleft()
            parts.appendleft(f'{head} {extra}')
            yield from self._update_virtual_cursor(parts)
        else:
            # showing all sections that names start with the head
            yield from get_heads(self._virtual_cursor, head)

    def _prepand_nop(self, data: Iterable[str]) -> Generator[str | Exception, None, None]:
        """
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by __process_fabric method or __mod methods. Final stream does not contain it.
        """
        yield '\n'
        yield from data

    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        if not value:
            return
        # little bit hacky here
        value = value.lower()
        if m := re.search(r'([-a-z0-9\/]+)\.(\d+)', value, re.I):
            value = value.replace(f'{m.group(1)}.{m.group(2)}', f'{m.group(1)} unit {m.group(2)}')
        parts = value.split()
        if parts[0] in self.keywords['top']:
            if len(parts) > 2 and (parts[1] in self.keywords['show'] or parts[1] in self.keywords['go']):
                self._virtual_cursor = self._tree
                yield from self._update_virtual_cursor(deque(parts[2:]))
        elif parts[0] in self.keywords['up']:
            if len(parts) > 2 and (parts[1] in self.keywords['show'] or parts[1] in self.keywords['go']):
                if self._cursor['name'] != 'root':
                    self._virtual_cursor = self._cursor['parent']
                yield from self._update_virtual_cursor(deque(parts[2:]))
        elif parts[0] in self.keywords['show'] or parts[0] in self.keywords['go']:
            if len(parts) != 1:
                self._virtual_cursor = self._cursor
                yield from self._update_virtual_cursor(deque(parts[1:]))

    def get_virtual_from(self, value: str) -> str:
        value = value.lower()
        # little bit hacky here
        if m := re.search(r'([-a-z0-9\/]+)\.(\d+)', value, re.I):
            value = value.replace(f'{m.group(1)}.{m.group(2)}', f'{m.group(1)} unit {m.group(2)}')
        parts = value.split()
        if len(parts) < 2:
            return ''
        first = ''
        if parts[0] == 'top' or parts[0] == 'up':
            if len(parts) < 3:
                return ''
            first = parts[0]
            parts = parts[1:]
        if parts[0] not in self.keywords['show'] and parts[0] not in self.keywords['go']:
            return ''
        new_value = ' '.join(parts[1:])
        if self._virtual_cursor['name'] == 'root':
            return new_value
        path = self._virtual_cursor['path']
        path = path.replace('inactive: ', '')
        rpath = self._cursor['path'] if self._cursor['name'] != 'root' else ''
        if not first and self._cursor['name'] != 'root':
            path = path.replace(self._cursor['path'], '', 1)
        spath = path.replace(self.delimiter, ' ')
        spath = spath.strip().lower()
        if first == 'up':
            if path.startswith(rpath):
                # when a user tries to do `up show x y`
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

    def mod_wildcard(
        self, data: Iterator[str] | Generator[str | Exception, None, None], args: list[str]
    ) -> Generator[str | Exception, None, None]:
        # passthrough modificator
        if not data or len(args) != 1:
            yield FabricException('Incorrect arguments for "wildcard".')
        try:
            re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "wildcard": {args[0]}.')
        else:
            try:
                head = next(data)
                if isinstance(head, Exception):
                    yield head
                else:
                    yield '\n'
                    yield from lazy_wc_parser(data, '', args[0], self.delimiter)
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
        remote_context: Optional[JunOSContext] = None
        for elem in self.__store:
            if elem.name == context_name:
                remote_context = elem
                break
        else:
            yield FabricException('Remote context has not been found.')
        assert remote_context is not None  # mypy's satisfier
        target: Root | Node = None
        peer: Root | Node = None
        if jump_node:
            target = jump_node
            path = deque(jump_node['path'].split(self.delimiter))
            peer = search_node(path, remote_context.tree)
        else:
            target = self._cursor
            if target['name'] != 'root':
                path = deque(target['path'].split(self.delimiter))
                peer = search_node(path, remote_context.tree)
            else:
                peer = remote_context.tree
        if not peer:
            yield FabricException(f'Remote context lacks this path: {target["path"].replace(self.delimiter, " ")}.')
        tree = compare_nodes(target, peer)
        if 'name' not in tree:
            yield FabricException('Fail to compare the contexts. The same content?')
        yield '\n'
        yield from draw_diff_tree(tree, tree['name'])

    def mod_inactive(self, jump_node: Optional[Node] = []) -> Generator[str | Exception, None, None]:
        node = self._cursor if not jump_node else jump_node
        tree = search_inactives(node)
        yield '\n'
        yield from draw_inactive_tree(tree, tree['name'])

    def mod_stubs(self, jump_node: Optional[Node] = []) -> Generator[str | Exception, None, None]:
        node = self._cursor if not jump_node else jump_node
        if not node['stubs']:
            yield FabricException('No stubs at this level.')
        yield '\n'
        yield from node['stubs']

    def mod_sections(self, jump_node: Optional[Node] = []) -> Generator[str | Exception, None, None]:
        node = self._cursor if not jump_node else jump_node
        if not node['children']:
            yield FabricException('No sections at this level.')
        yield '\n'
        yield from map(lambda x: x['name'], node['children'])

    def mod_contains(self, args: list[str], jump_node: Optional[Node] = []) -> Generator[str | Exception, None, None]:
        def replace_path(source: str, path: str) -> str:
            return source.replace(path, '').replace(self.delimiter, ' ').strip()

        def lookup_child(node: Root | Node, path: str) -> Generator[str, None, None]:
            for child in node['children']:
                yield from lookup_child(child, path)
            if re.search(args[0], node['name']):
                yield replace_path(node['path'], path)
            for stub in filter(lambda x: re.search(args[0], x), node['stubs']):
                yield f'{replace_path(node["path"], path)}: "{stub}"'

        if len(args) != 1:
            yield FabricException('There must be one argument for "contains".')
        node = self._cursor if not jump_node else jump_node
        if not node['children']:
            yield FabricException('No sections at this level.')
        try:
            re.compile(args[0])
        except re.error:
            yield FabricException(f'Incorrect regular expression for "contains": {args[0]}.')
        yield '\n'
        yield from lookup_child(node, node['path'] if 'path' in node else '')

    def _process_fabric(
        self, data: Iterable[str], mods: list[list[str]], *, jump_node: Optional[Node] = None, banned: list[str] = []
    ) -> Response:
        def check_leading_mod(name: str, position: int, args_count: int, args_limit: int = 0) -> None:
            if position:
                raise FabricException(f'Incorrect position of "{name}".')
            if args_count != args_limit:
                raise FabricException(f'Incorrect number of arguments for "{name}". Must be {args_limit}.')

        is_flat_out: bool = True
        recol_data = self._prepand_nop(data)
        try:
            for number, elem in enumerate(mods):
                command = elem[0]
                if command in banned:
                    raise FabricException(f'You cannot use the "{command}" with this main command.')
                if command in self.keywords['filter']:
                    recol_data = self.mod_filter(recol_data, elem[1:])
                elif command in self.keywords['wildcard']:
                    recol_data = self.mod_wildcard(recol_data, elem[1:])
                    is_flat_out = False
                elif command in self.keywords['save']:
                    recol_data = lazy_provide_config(recol_data, block=' ' * self.spaces)
                    recol_data = self.mod_save(recol_data, elem[1:])
                    break
                elif command in self.keywords['count']:
                    recol_data = self.mod_count(recol_data, elem[1:])
                    break
                elif command in self.keywords['diff']:
                    check_leading_mod(command, number, len(elem[1:]), 1)
                    recol_data = self.mod_diff(elem[1:], jump_node)
                elif command in self.keywords['inactive']:
                    check_leading_mod(command, number, len(elem[1:]))
                    recol_data = self.mod_inactive(jump_node)
                    is_flat_out = False
                elif command in self.keywords['stubs']:
                    check_leading_mod(command, number, len(elem[1:]))
                    recol_data = self.mod_stubs(jump_node)
                elif command in self.keywords['sections']:
                    check_leading_mod(command, number, len(elem[1:]))
                    recol_data = self.mod_sections(jump_node)
                elif command in self.keywords['contains']:
                    check_leading_mod(command, number, len(elem[1:]), 1)
                    recol_data = self.mod_contains(elem[1:], jump_node)
                else:
                    raise FabricException(f'Unknown modificator "{command}".')
            head = next(recol_data)
            if isinstance(head, Exception):
                raise head
            if is_flat_out:
                return ContextResponse.success(map(lambda x: x.strip() if type(x) is str else x, recol_data))
            return ContextResponse.success(lazy_provide_config(recol_data, block=' ' * self.spaces))
        except FabricException as err:
            return AlertResponse.error(f'{err}')
        except (AttributeError, IndexError) as err:
            return AlertResponse.error(f'Unknown error from the fabric #001: {err}')
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
                if self._tree['version']:
                    return ContextResponse.success(self._tree['version'])
                return AlertResponse.error('No version has been found.')
            else:
                if node := search_node(args, self._cursor):
                    try:
                        data = lazy_parser(self.content, node['path'], self.delimiter)
                        next(data)
                        if mods:
                            return self._process_fabric(data, mods, jump_node=node)
                        return ContextResponse.success(lazy_provide_config(data, block=' ' * self.spaces))
                    except Exception as err:
                        return AlertResponse.error(f'{err}')
                return AlertResponse.error('This path is not correct.')
        else:
            data = iter(self.content)
            if self._cursor['name'] != 'root':
                try:
                    data = lazy_parser(data, self._cursor['path'], self.delimiter)
                    next(data)
                except Exception as err:
                    return AlertResponse.error(f'{err}')
            if mods:
                return self._process_fabric(data, mods)
            return ContextResponse.success(lazy_provide_config(data, block=' ' * self.spaces))

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
                if self._cursor['name'] == 'root':
                    return AlertResponse.error("You can't do a negative lookahead from the top.")
                temp = self._cursor
                self._cursor = self._cursor['parent']
                result = self.command_show(args, mods)
                self._cursor = temp
                return result
            elif arg.isdigit():
                if len(args) != 1:
                    return AlertResponse.error('There must be one argument for "up".')
                steps = min(int(arg), UP_LIMIT)
            else:
                return AlertResponse.error(f'Incorrect argument for "up": {arg}.')
        if self._cursor['name'] == 'root':
            return AlertResponse.success()
        current = self._cursor
        while steps:
            if current['name'] == 'root':
                break
            current = current['parent']
            steps -= 1
        self._cursor = current
        return AlertResponse.success()
