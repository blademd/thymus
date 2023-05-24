from __future__ import annotations

import os
import sys
import json

from typing import TYPE_CHECKING, Any
from collections import deque
from dataclasses import dataclass

from pygments.styles import get_all_styles


if TYPE_CHECKING:

    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Callable, Iterable
    else:
        from typing import Callable, Iterable

CONFIG_PATH = 'thymus/settings'
SAVES_PATH = 'thymus/saves'
CONFIG_NAME = 'global.json'
MIN_CODE_WIDTH = 1500
MAX_CODE_WIDTH = 3000
DEFAULT_THEME = 'monokai'


@dataclass
class SettingsResponse:
    status: str  # error or success
    value: 'Iterable[str]'

class AppSettings:
    __slots__ = (
        '__code_width',
        '__theme',
        '__errors',
        '__is_dir',
    )

    @property
    def code_width(self) -> int:
        return self.__code_width

    @property
    def theme(self) -> str:
        return self.__theme

    @property
    def styles(self) -> list[str]:
        return get_all_styles()

    @code_width.setter
    def code_width(self, value: int) -> None:
        if type(value) is not int or value > MAX_CODE_WIDTH or value < MIN_CODE_WIDTH:
            raise ValueError(f'Code width must be >= {MIN_CODE_WIDTH} and <= {MAX_CODE_WIDTH}.')
        self.__code_width = value

    @theme.setter
    def theme(self, value: str) -> None:
        if value not in self.styles:
            raise ValueError('Unknown theme.')
        self.__theme = value

    def __init__(self) -> None:
        self.__code_width: int = MIN_CODE_WIDTH
        self.__theme: str = DEFAULT_THEME
        self.__errors: deque[str] = deque()
        self.__is_dir: bool = True
        self.__load_configuration()

    def __load_configuration(self) -> None:
        try:
            if not os.path.exists(SAVES_PATH):
                os.mkdir(SAVES_PATH)
            if not os.path.exists(CONFIG_PATH):
                os.mkdir(CONFIG_PATH)
            else:
                if not os.path.isdir(CONFIG_PATH):
                    self.__errors.append(f'The directory "{CONFIG_PATH}" cannot be created.')
                    self.__is_dir = False
                    return
            if not os.path.exists(f'{CONFIG_PATH}/{CONFIG_NAME}'):
                self.__save_settings()
            else:
                with open(f'{CONFIG_PATH}/{CONFIG_NAME}', encoding='utf-8') as f:
                    data: dict[str, Any] = json.load(f)
                    self.theme = data['theme']
                    self.code_width = int(data['code_width'])
        except Exception as err:
            if len(err.args):
                err_line = ' '.join(err.args)
                self.__errors.append(f'Something went wrong: "{err_line}".')

    def __save_settings(self) -> None:
        if not self.__is_dir:
            return
        with open(f'{CONFIG_PATH}/{CONFIG_NAME}', 'w', encoding='utf-8') as f:
            data = {
                'code_width': self.code_width,
                'theme': self.theme,
            }
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())

    def playback(self, logger: 'Callable[[str], None]') -> None:
        while self.__errors:
            error = self.__errors.popleft()
            logger(error)

    def process_command(self, command: str) -> SettingsResponse:
        if not command.startswith('global '):
            return SettingsResponse('error', iter(['Unknown global command.']))
        parts = command.split()
        if len(parts) < 3:
            return SettingsResponse('error', iter(['Incomplete global command.']))
        subcommand = parts[1]
        try:
            if subcommand == 'show':
                if len(parts) > 3:
                    return SettingsResponse('error', iter(['Too many arguments for `global show` command.']))
                arg = parts[2]
                if arg == 'themes':
                    result: list[str] = []
                    result.append('* -- current theme')
                    for theme in self.styles:
                        result.append(f'{theme}*' if theme == self.theme else theme)
                    return SettingsResponse('success', iter(result))
                else:
                    return SettingsResponse('error', iter(['Unknown argument for `global show` command.']))
            elif subcommand == 'set':
                if len(parts) < 4:
                    return SettingsResponse('error', iter(['Incomplete `global set` command.']))
                arg = parts[2]
                if arg == 'theme':
                    if len(parts) > 4:
                        return SettingsResponse('error', iter(['Too many arguments for `global set` command.']))
                    value = parts[3]
                    self.theme = value
                    self.__save_settings()
                    return SettingsResponse('success', iter([f'+ The theme was changed to {self.theme}.']))  # TEMP
                else:
                    return SettingsResponse('error', iter(['Unknown argument for `global set` command.']))
            else:
                return SettingsResponse('error', iter(['Unknown global command.']))
        except ValueError as err:
            if len(err.args):
                return SettingsResponse('error', iter(err.args))
        return SettingsResponse('error', [])
