from __future__ import annotations

import sys
import re
import os
import shlex
import time

from collections import deque
from typing import TypedDict, TYPE_CHECKING

if sys.version_info.major == 3 and sys.version_info.minor >= 9:
    from collections.abc import Generator, Iterable, Callable
else:
    from typing import Generator, Iterable, Callable

from functools import reduce
from .parsers.jparser import (
    construct_tree,
    search_node,
    lazy_parser,
    lazy_provide_config,
    lazy_wc_parser,
    compare_nodes,
    draw_diff_tree,
    search_inactives,
    draw_inactive_tree,
)

if TYPE_CHECKING:
    from .parsers.jparser import Root, Node


NOS_LIST = (
    'junos',
)

def err_print(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)


class FabricException(Exception):
    pass

class Context(TypedDict):
    name: str
    config_path: str
    nos: str
    config: list[str]
    tree: 'Root'
    cursor: 'Root | Node'

class SystemWrapper:
    __slots__ = (
        '_base_prompt',
        '__order',
        '__contexts',
        '__current'
    )
    __base_prompt = 'thymus> '

    def __init__(self) -> None:
        self.__order: int = 0
        self.__contexts: dict[str, Context] = {}
        self.__current: Context = {}

    def __open_config(self, args: deque[str]) -> bool:
        if len(args) != 2:
            err_print('Incorrect arguments for "open".')
            return False
        nos = args.popleft()
        config_path = args.popleft()
        nos = nos.lower()
        if nos not in NOS_LIST:
            err_print(f'Unknown network OS "{nos}".')
            return False
        config: list[str] = []
        try:
            with open(config_path, encoding='utf-8-sig', errors='replace') as f:
                config = f.readlines()
        except IOError:
            err_print('Cannot open the file.')
            return False
        tree = construct_tree(config)
        if not tree:
            err_print('Fail to create a tree for this config.')
            return False
        context_name = f'vty{self.__order}'
        self.__contexts[context_name] = Context(
            name=context_name,
            nos=nos,
            config_path=config_path,
            config=config,
            tree=tree,
            cursor=tree
        )
        self.__current = self.__contexts[context_name]
        self.__order += 1
        return True

    def __switch_context(self, args: deque[str]) -> bool:
        if len(args) != 1:
            err_print('Incorrect arguments for "switch".')
            return False
        context_name = args.popleft()
        if context_name not in self.__contexts or not self.__contexts[context_name]:
            err_print(f'No such a context "{context_name}".')
            return False
        self.__current = self.__contexts[context_name]
        print(f'Context is switched to "{context_name}".')
        return True

    def __new_prompt(self) -> str:
        if not self.__current:
            return self.__base_prompt
        top = 'root'
        if self.__current['cursor']['name'] != 'root':
            top = self.__current['cursor']['path']
            top = top.replace('^', ' ')  # TODO: delimiter
        nos = self.__current['nos']
        context_name = self.__current['name']
        return f'[{top}]\nt:{nos}({context_name})> '

    def __go(self, args: deque[str]) -> bool:
        if not self.__current:
            return False
        node = search_node(args, self.__current['cursor'])
        if not node:
            err_print('Incorrect path.')
            return False
        self.__current['cursor'] = node
        return True

    def __up(self, args: deque[str] = []) -> bool:
        if args and len(args) != 1:
            err_print('Incorrect arguments for "up".')
            return False
        if args and len(args[0]) > 2:
            err_print('Incorrect length for "up".')
            return False
        if not self.__current:
            return False
        if self.__current['cursor']['name'] == 'root':
            return False
        num = 1
        if args and args[0].isdigit():
            num = int(args[0])
        node = self.__current['cursor']
        while num:
            if node['name'] == 'root':
                break
            node = node['parent']
            num -= 1
        self.__current['cursor'] = node
        return True

    def __top(self, args: deque[str] = [], mods: list[list[str]] = []) -> bool:
        if args and len(args) < 2:
            err_print('Incorrect arguments for "top".')
            return False
        if not self.__current:
            return False
        if self.__current['cursor']['name'] == 'root':
            return False
        if args:
            command = args[0]
            if command == 'show':
                temp = self.__current['cursor']
                self.__current['cursor'] = self.__current['tree']
                self.__process_parsed_command(args, mods)
                self.__current['cursor'] = temp
            else:
                err_print('Incorrect sub-command for "top".')
            return False  # there is no move actually so False
        else:
            self.__current['cursor'] = self.__current['tree']
        return True

    def __filter(self, args: deque[str], source: Iterable[str]) -> Generator[str, None, None]:
        # passthrough modificator
        # if it fails to compile a user-defined regexp it will use the default which always matches every line
        if len(args) != 1 or not source:
            raise FabricException('Incorrect arguments for "filter".')
        re_expr = re.compile(r'^.+$', re.DOTALL)  # default regexp
        expr = args.pop()
        try:
            re_expr = re.compile(expr, re.DOTALL)
        except re.error:
            err_print('Incorrect expression for "filter".')
        yield from filter(lambda x: re_expr.search(x), source)

    def __save(self, args: deque[str], source: Iterable[str]) -> None:
        # terminating modificator
        if len(args) != 1 or not source:
            raise FabricException('Incorrect arguments for "save".')
        dest = args.pop()
        with open(dest, 'w', encoding='utf-8-sig') as f:
            for line in source:
                f.write(f'{line}\n')
            f.flush()
            os.fsync(f.fileno())

    def __wc_filter(self, args: deque[str], source: Iterable[str]) -> Generator[str, None, None]:
        # passthrough modificator
        if len(args) != 1 or not source:
            raise FabricException('Incorrect arguments for "wc_filter".')
        if not self.__current:
            raise FabricException()
        expr = args.pop()
        yield from lazy_wc_parser(source, '', expr)

    def __count(self, args: deque[str], source: Iterable[str]) -> None:
        # terminating modificator
        if args:
            raise FabricException('Incorrect arguments for "count".')
        counter = 0
        for _ in filter(lambda x: x, source):
            counter += 1
        print(f'Count: {counter}.')

    def __compare(self, args: deque[str], extra_args: deque[str] = []) -> Generator[str, None, None]:
        # leading paththrough modificator
        if len(args) != 1:
            raise FabricException('Incorrect arguments for "compare".')
        if not self.__current:
            raise FabricException()
        context_name = args.pop()
        if context_name == self.__current['name']:
            raise FabricException('The same context.')
        context = self.__contexts.get(context_name)
        if not context:
            raise FabricException('No such a context.')
        target_node: Root | Node = {}
        peer_node: Root | Node = {}
        delimiter = self.__current['tree']['delimiter']
        if not extra_args:
            target_node = self.__current['cursor']
            if self.__current['cursor']['name'] != 'root':
                path = self.__current['cursor']['path']
                peer_node = search_node(deque(path.split(delimiter)), context['tree'])
            else:
                peer_node = context['tree']
        else:
            path = extra_args.pop()
            target_node = search_node(deque(path.split(delimiter)), self.__current['tree'])
            peer_node = search_node(deque(path.split(delimiter)), context['tree'])
        if not peer_node:
            raise FabricException('Peer context lacks this path.')
        extra_tree = compare_nodes(target_node, peer_node)
        yield from draw_diff_tree(extra_tree, extra_tree['name'])

    def header(method: Callable) -> Callable:
        # leading paththrough modificators
        def inner(self: SystemWrapper, args: deque[str], extra_args: deque[str] = []) -> Generator[str, None, None]:
            if args:
                raise FabricException('Incorrect arguments.')
            if not self.__current:
                raise FabricException()
            node: 'Root | Node' = self.__current['cursor']
            if extra_args:
                path = extra_args.pop()
                delimiter = self.__current['tree']['delimiter']
                node = search_node(deque(path.split(delimiter)), self.__current['tree'])
            yield from method(node)
        return inner

    @header
    def __inactive(node: 'Root | Node') -> Generator[str, None, None]:
        extra_tree = search_inactives(node)
        if not extra_tree:
            raise FabricException('No results.')
        yield from draw_inactive_tree(extra_tree, extra_tree['name'])

    @header
    def __stubs(node: 'Root | Node') -> Generator[str, None, None]:
        if not node['stubs']:
            raise FabricException('No stubs.')
        yield from node['stubs']

    @header
    def __sections(node: 'Root | Node') -> Generator[str, None, None]:
        if not node['children']:
            raise FabricException('No sections.')
        for child in node['children']:
            yield child['name']

    def __process_fabric(self, mods: list[list[str]], source: Iterable[str], extra_args: deque[str] = []) -> None:
        try:
            data = source
            is_flat = True
            for idx, elem in enumerate(mods):
                command = elem[0]
                if command == 'filter':
                    data = self.__filter(deque(elem[1:]), data)
                elif command == 'wc_filter':
                    data = self.__wc_filter(deque(elem[1:]), data)
                    is_flat = False
                elif command == 'save':
                    data = lazy_provide_config(data)
                    data = self.__save(deque(elem[1:]), data)
                elif command == 'count':
                    data = self.__count(deque(elem[1:]), data)
                elif command == 'compare':
                    if idx:
                        raise FabricException('Incorrect position of "compare".')
                    data = self.__compare(deque(elem[1:]), extra_args)
                    is_flat = False
                elif command == 'inactive':
                    if idx:
                        raise FabricException('Incorrect position of "inactive".')
                    data = self.__inactive(deque(elem[1:]), extra_args)
                    is_flat = False
                elif command == 'stubs':
                    if idx:
                        raise FabricException('Incorrect position of "stubs".')
                    data = self.__stubs(deque(elem[1:]), extra_args)
                elif command == 'sections':
                    if idx:
                        raise FabricException('Incorrect position of "sections".')
                    data = self.__sections(deque(elem[1:]), extra_args)
                else:
                    raise FabricException('No such a command.')
            if data:
                if is_flat:
                    for line in data:
                        print(line.strip())
                else:
                    for line in lazy_provide_config(data):
                        print(line)
        except (AttributeError, IndexError) as err:
            err_print(f'Line of modificators is improper. Err.: {err}.')
        except FabricException as err:
            if err:
                err_print(err)
        except KeyboardInterrupt:
            print('Interrupted.')

    def __show(self, args: deque[str] = [], mods: list[list[str]] = []) -> bool:
        if args:
            if args[0] in ('ver', 'version',):
                if len(args) > 1:
                    err_print('Incorrect arguments for "show version".')
                    return False
                if not self.__current:
                    return False
                ver = self.__current['tree']['version']
                print(ver) if ver else err_print('No version has been detected.')
            else:
                if not self.__current:
                    return False
                if node := search_node(args, self.__current['cursor']):
                    data = lazy_parser(self.__current['config'], node['path'])
                    next(data)
                    if mods:
                        args.append(node['path'])
                        self.__process_fabric(mods, data, extra_args=args)
                    else:
                        for line in lazy_provide_config(data):
                            print(line)
                else:
                    err_print('Unknown path.')
                    return False
        else:
            if not self.__current:
                return False
            data = self.__current['config']
            if self.__current['cursor']['name'] != 'root':
                data = lazy_parser(self.__current['config'], self.__current['cursor']['path'])
                next(data)
            if mods:
                self.__process_fabric(mods, data)
            else:
                for line in lazy_provide_config(data):
                    print(line)
        return False

    def __process_parsed_command(self, head: deque[str], args: list[list[str]]) -> str:

        def move_or_warn(command: str) -> str:
            if not self.__current or self.__current['cursor']['name'] == 'root':
                err_print('Unknown command.')
                return ''
            head.appendleft(command)
            if self.__go(head):
                return self.__new_prompt()
            else:
                err_print('Unknown path or command.')
                return ''
        command = head.popleft()
        if head:
            # we have additional args for a command
            if command == 'help':
                pass
            elif command == 'open':
                if self.__open_config(head):
                    return self.__new_prompt()
            elif command == 'switch':
                if self.__switch_context(head):
                    return self.__new_prompt()
            elif command == 'go':
                if self.__go(head):
                    return self.__new_prompt()
            elif command == 'up':
                if self.__up(head):
                    return self.__new_prompt()
            elif command == 'top':
                if self.__top(head, args):
                    return self.__new_prompt()
            elif command == 'show':
                self.__show(head, args)
            else:
                return move_or_warn(command)
        else:
            # this is a singleton command
            if command == 'help':
                pass
            elif command == 'show':
                self.__show(mods=args)
            elif command == 'up':
                if self.__up():
                    return self.__new_prompt()
            elif command == 'top':
                if self.__top():
                    return self.__new_prompt()
            else:
                return move_or_warn(command)
        return ''

    def process_command(self, user_input: str, prompt: str) -> str:
        args = reduce(
            lambda acc, x: acc[:-1] + [acc[-1] + [x]] if x != '|' else acc + [[]],
            shlex.split(user_input),
            [[]]
        )
        head = deque(args[0])
        try:
            result = self.__process_parsed_command(head, args[1:])
            if not result:
                return prompt
            return result
        except KeyboardInterrupt:
            print('Interrupted.')
        return prompt

def main() -> None:
    print('Hello %username%! This is a CLI tool for reading network devices\' config files.')
    print('Enter "help" to list supported commands.')
    prompt = 'thymus> '
    cli = SystemWrapper()
    while True:
        user_input = input(prompt)
        if not user_input:
            print(prompt)
            continue
        user_input = user_input.strip()
        if user_input in ('exit', 'quit', 'stop', 'logout',):
            print('Goodbye!')
            break
        t = time.time()
        prompt = cli.process_command(user_input, prompt)
        print(f'\nCommand execution time is {time.time() - t} secs.')


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
