from __future__ import annotations

from typing import TYPE_CHECKING

from .contexts import (
    JunOSContext,
    IOSContext,
    EOSContext
)

import sys
import time


if TYPE_CHECKING:
    from .contexts import Context

NOS_LIST = {
    'junos': JunOSContext,
    'ios': IOSContext,
    'eos': EOSContext,
}

def err_print(*args, **kwargs) -> None:
    print(*args, file=sys.stderr, **kwargs)

def usage() -> None:
    err_print('Usage is not written yet.')


class SystemWrapper:
    __slots__: tuple[str, ...] = (
        '__base_prompt',
        '__contexts',
        '__current',
        '__number',
    )

    def __init__(self) -> None:
        self.__base_prompt: str = 'thymus> '
        self.__contexts: dict[str, Context] = {}
        self.__current: Context = {}
        self.__number: int = 0

    def __open_config(self, args: list[str]) -> None:
        if len(args) != 2:
            err_print('Incorrect arguments for "open". Usage: "open nos_type file".')
            return
        nos = args[0]
        config_path = args[1]
        nos = nos.lower()
        if nos not in NOS_LIST:
            err_print(f'Unknown network OS: {nos}. Use:')
            for key in NOS_LIST:
                err_print(f'\t{key}')
            return
        config: list[str] = []
        try:
            with open(config_path, encoding='utf-8-sig', errors='replace') as f:
                config = f.readlines()
        except FileNotFoundError:
            err_print(f'Cannot open the file: {config_path}.')
            return
        context_name = f'vty{self.__number}'
        self.__contexts[context_name] = NOS_LIST[nos](context_name, config)
        self.__current = self.__contexts[context_name]
        self.__number += 1

    def __switch_context(self, args: list[str]) -> None:
        if len(args) != 1:
            err_print('Incorrect arguments for "switch".')
            return
        context_name = args[0]
        if context_name not in self.__contexts or not self.__contexts[context_name]:
            err_print(f'No such a context: {context_name}.')
            return
        self.__current = self.__contexts[context_name]
        print(f'Context is switched to: {context_name}.')

    def __new_prompt(self) -> str:
        if not self.__current:
            return self.__base_prompt
        top = 'root'
        if self.__current.prompt:
            top = self.__current.prompt
        top = top.replace(self.__current.delimiter, ' ')
        context_name = self.__current.name
        nos_type = self.__current.nos_type.lower()
        return f'[{top}]\nthymus:{nos_type}({context_name})> '

    def process_command(self, value: str) -> str:
        if value.startswith('set name'):
            return self.__base_prompt
        parts = value.split()
        command = parts[0]
        if command == 'open':
            self.__open_config(parts[1:])
        elif command == 'switch':
            self.__switch_context(parts[1:])
        elif command == 'help':
            usage()
        else:
            if not self.__current:
                err_print('Unknown command or no valid context.')
                return self.__base_prompt
            result = self.__current.on_enter(value)
            out = print if result.is_ok else err_print
            for line in result.value:
                if line:
                    out(line)
            return self.__new_prompt()
        return self.__base_prompt


def main() -> None:
    print('Hello, %username%!')
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
        prompt = cli.process_command(user_input)
        print(f'\nCommand execution time is {time.time() - t} secs.')
