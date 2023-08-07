from __future__ import annotations

from typing import TYPE_CHECKING
from collections import deque

from .context import (
    Context,
    FabricException,
    UP_LIMIT,
)
from ..responses import (
    ContextResponse,
    AlertResponse,
)
from ..parsers.junos import (
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
from ..lexers import JunosLexer

import sys
import re


if TYPE_CHECKING:
    from typing import Optional
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Generator, Iterable
    else:
        from typing import Generator, Iterable
    from logging import Logger

    from ..responses import Response
    from ..parsers.junos import (
        Root,
        Node,
    )


class JunOSContext(Context):
    __slots__: tuple[str, ...] = (
        '__tree',
        '__cursor',
        '__virtual_cursor',
    )
    __store: list[JunOSContext] = []
    lexer: JunosLexer = JunosLexer

    @property
    def prompt(self) -> str:
        if self.__cursor['name'] == 'root':
            return ''
        else:
            return self.__cursor['path']

    @property
    def tree(self) -> Root:
        return self.__tree

    @property
    def nos_type(self) -> str:
        return 'JUNOS'

    def __init__(
        self,
        name: str,
        content: list[str],
        *,
        encoding: str,
        settings: dict[str, str | int],
        logger: Logger
    ) -> None:
        super().__init__(name, content, encoding=encoding, settings=settings, logger=logger)
        self.__tree: Root = construct_tree(self.content, self.delimiter)
        if not self.__tree or not self.__tree.get('children'):
            raise Exception(f'{self.nos_type}. Impossible to build a tree.')
        self.__store.append(self)
        self.__cursor: Root | Node = self.__tree
        self.__virtual_cursor: Root | Node = self.__tree
        self.spaces = 2
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
        if hasattr(self, '__tree') and self.__tree:
            self.__logger.debug('Trying to apply settings with a completed tree.')
            return
        super().apply_settings(settings)

    def __update_virtual_cursor(self, parts: list[str]) -> Generator[str, None, None]:
        if not parts:
            return
        for child in self.__virtual_cursor['children']:
            if child['name'] == parts[0]:
                self.__virtual_cursor = child
                if parts[1:]:
                    yield from self.__update_virtual_cursor(parts[1:])
                else:
                    yield child['name']
                break
            elif (len(parts) > 1 and child['name'] == ' '.join(parts[:2])):
                self.__virtual_cursor = child
                if parts[2:]:
                    yield from self.__update_virtual_cursor(parts[2:])
                else:
                    yield child['name']
                break
        else:
            value = parts[0]
            if len(parts) > 1:
                value = f'{parts[0]} {parts[1]}'
            for child in self.__virtual_cursor['children']:
                if re.search(rf'^{value}', child['name'], re.I):
                    yield child['name']

    def __prepand_nop(self, data: Iterable[str]) -> Generator[str, None, None]:
        '''
        This method simply adds a blank line to a head of the stream. If the stream is not lazy, it also converts it.
        The blank line is then eaten by __process_fabric method or __mod methods. Final stream does not contain it.
        '''
        yield '\n'
        yield from data

    def update_virtual_cursor(self, value: str) -> Generator[str, None, None]:
        if not value:
            return
        # little bit hacky here
        if m := re.search(r'([-a-z0-9\/]+)\.(\d+)', value, re.I):
            value = value.replace(f'{m.group(1)}.{m.group(2)}', f'{m.group(1)} unit {m.group(2)}')
        parts = value.split()
        if parts[0] in self.keywords['top']:
            if len(parts) > 2 and (parts[1] in self.keywords['show'] or parts[1] in self.keywords['go']):
                self.__virtual_cursor = self.__tree
                yield from self.__update_virtual_cursor(parts[2:])
        elif parts[0] in self.keywords['show'] or parts[0] in self.keywords['go']:
            if len(parts) != 1:
                self.__virtual_cursor = self.__cursor
                yield from self.__update_virtual_cursor(parts[1:])

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
        if parts[0] not in self.keywords['show'] and parts[0] not in self.keywords['go']:
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

    def mod_wildcard(self, data: Iterable[str], args: list[str]) -> Generator[str | FabricException, None, None]:
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
        remote_context: JunOSContext = None
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
            path = deque(jump_node['path'].split(self.delimiter))
            peer = search_node(path, remote_context.tree)
        else:
            target = self.__cursor
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

    def mod_inactive(self, jump_node: Optional[Node] = []) -> Generator[str | FabricException, None, None]:
        node = self.__cursor if not jump_node else jump_node
        tree = search_inactives(node)
        yield '\n'
        yield from draw_inactive_tree(tree, tree['name'])

    def mod_stubs(self, jump_node: Optional[Node] = []) -> Generator[str | FabricException, None, None]:
        node = self.__cursor if not jump_node else jump_node
        if not node['stubs']:
            yield FabricException('No stubs at this level.')
        yield '\n'
        yield from node['stubs']

    def mod_sections(self, jump_node: Optional[Node] = []) -> Generator[str | FabricException, None, None]:
        node = self.__cursor if not jump_node else jump_node
        if not node['children']:
            yield FabricException('No sections at this level.')
        yield '\n'
        yield from map(lambda x: x['name'], node['children'])

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

        is_flat_out: bool = True
        data = self.__prepand_nop(data)
        try:
            for number, elem in enumerate(mods):
                command = elem[0]
                if command in self.keywords['filter']:
                    data = self.mod_filter(data, elem[1:])
                elif command in self.keywords['wildcard']:
                    data = self.mod_wildcard(data, elem[1:])
                    is_flat_out = False
                elif command in self.keywords['save']:
                    data = lazy_provide_config(data, block=' ' * self.spaces)
                    data = self.mod_save(data, elem[1:])
                    break
                elif command in self.keywords['count']:
                    data = self.mod_count(data, elem[1:])
                    break
                elif command in self.keywords['diff']:
                    __check_leading_mod(command, number, len(elem[1:]), 1)
                    data = self.mod_diff(elem[1:], jump_node)
                elif command in self.keywords['inactive']:
                    __check_leading_mod(command, number, len(elem[1:]))
                    data = self.mod_inactive(jump_node)
                    is_flat_out = False
                elif command in self.keywords['stubs']:
                    __check_leading_mod(command, number, len(elem[1:]))
                    data = self.mod_stubs(jump_node)
                elif command in self.keywords['sections']:
                    __check_leading_mod(command, number, len(elem[1:]))
                    data = self.mod_sections(jump_node)
                else:
                    raise FabricException(f'Unknown modificator "{command}".')
            head: str | FabricException = next(data)
            if isinstance(head, Exception):
                raise head
            if is_flat_out:
                return ContextResponse.success(map(lambda x: x.strip(), data))
            return ContextResponse.success(lazy_provide_config(data, block=' ' * self.spaces))
        except FabricException as err:
            return AlertResponse.error(f'{err}')
        except (AttributeError, IndexError) as err:
            return AlertResponse.error(f'Unknown error from the fabric #001: {err}')
        except StopIteration:
            return AlertResponse.error('Unknown error from the fabric #002.')

    def command_show(self, args: deque[str] = [], mods: list[list[str]] = []) -> Response:
        if args:
            first_arg = args[0]
            if first_arg in self.keywords['version']:
                if len(args) > 1:
                    return AlertResponse.error('Too many arguments for "version".')
                if self.__tree['version']:
                    return ContextResponse.success(self.__tree['version'])
                return AlertResponse.error('No version has been found.')
            else:
                if node := search_node(args, self.__cursor):
                    try:
                        data = lazy_parser(self.content, node['path'], self.delimiter)
                        next(data)
                        if mods:
                            return self.__process_fabric(data, mods, jump_node=node)
                        return ContextResponse.success(lazy_provide_config(data, block=' ' * self.spaces))
                    except Exception as err:
                        return AlertResponse.error(f'{err}')
                return AlertResponse.error('This path is not correct.')
        else:
            data = iter(self.content)
            if self.__cursor['name'] != 'root':
                try:
                    data = lazy_parser(data, self.__cursor['path'], self.delimiter)
                    next(data)
                except Exception as err:
                    return AlertResponse.error(f'{err}')
            if mods:
                return self.__process_fabric(data, mods)
            return ContextResponse.success(lazy_provide_config(data, block=' ' * self.spaces))

    def command_go(self, args: deque[str]) -> Response:
        if not args:
            return AlertResponse.error('Not enough arguments for "go".')
        if node := search_node(args, self.__cursor):
            self.__cursor = node
            return AlertResponse.success()
        return AlertResponse.error('This path is not correct.')

    def command_top(self, args: deque[str], mods: list[list[str]]) -> Response:
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
                if self.__cursor['name'] == 'root':
                    return AlertResponse.error('You can\'t do a negative lookahead from the top.')
                temp = self.__cursor
                self.__cursor = self.__cursor['parent']
                result = self.command_show()
                self.__cursor = temp
                return result
            elif arg.isdigit():
                steps = min(int(arg), UP_LIMIT)
            else:
                return AlertResponse.error(f'Incorrect argument for "up": {arg}.')
        if self.__cursor['name'] == 'root':
            return AlertResponse.success()
        current = self.__cursor
        while steps:
            if current['name'] == 'root':
                break
            current = current['parent']
            steps -= 1
        self.__cursor = current
        return AlertResponse.success()
