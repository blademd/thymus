'''
To define a new platform an author is required to decrale a dict with default settings. This dict MUST be named
as DEFAULT_platform, where platform is a name of the new platform. It MUST contain at least `spaces` key with an
appropriate value.
PLATFORMS dict MUST be updated with a key which is equal to the platform name. This key MUST be in a lower case.
For the key there is the only one value -- the previously defined DEFAULT_platform dict.
For AppSettings class a property with the platform name MUST be declared. A function for validating keys of the
platform's dict MUST be declared. This function MUST check all keys that are defined for the new platform's
dict. The name of the function MUST be: __validate_platform_key.
'''

from __future__ import annotations

from typing import TYPE_CHECKING
from copy import copy
from logging.handlers import RotatingFileHandler, BufferingHandler
from logging.config import fileConfig

from pygments.styles import get_all_styles

from . import __version__ as app_ver
from . import (
    CONFIG_PATH,
    CONFIG_NAME,
    LOGGING_DEFAULTS,
    LOGGING_FILE,
    LOGGING_FILE_DIR,
    LOGGING_FORMAT,
    LOGGING_CONF,
    LOGGING_CONF_DIR,
    LOGGING_CONF_ENCODING,
    LOGGING_FILE_MAX_SIZE_BYTES,
    LOGGING_FILE_MAX_INSTANCES,
    LOGGING_FILE_ENCODING,
    LOGGING_BUF_CAP,
    N_VALUE_LIMIT,
    SAVES_DIR,
    SCREENS_SAVES_DIR,
)
from .responses import SettingsResponse

import os
import sys
import json
import logging


if TYPE_CHECKING:
    from typing import Any
    if sys.version_info.major == 3 and sys.version_info.minor >= 9:
        from collections.abc import Callable
    else:
        from typing import Callable


DEFAULT_GLOBALS = {
    'theme': 'monokai',
    'filename_len': 256,
    'sidebar_limit': 64,
    'sidebar_strict_on_tab': 'on',
}
DEFAULT_JUNOS = {
    'spaces': 2,
}
DEFAULT_IOS = {
    'spaces': 1,
    'heuristics': 'off',
    'base_heuristics': 'on',
    'crop': 'off',
    'promisc': 'off',
}
DEFAULT_EOS = {
    'spaces': 2,
    'heuristics': 'off',
    'base_heuristics': 'on',
    'crop': 'off',
    'promisc': 'off',
}
DEFAULT_NXOS = {
    'spaces': 2,
    'heuristics': 'off',
    'base_heuristics': 'on',
    'crop': 'off',
}
PLATFORMS = {
    'junos': DEFAULT_JUNOS,
    'ios': DEFAULT_IOS,
    'eos': DEFAULT_EOS,
    'nxos': DEFAULT_NXOS,
}


class AppSettings:
    __slots__: tuple[str, ...] = (
        '__globals',
        '__platforms',
        '__logger',
        '__is_dir',
        '__is_alert',
    )

    @property
    def globals(self) -> dict[str, str | int]:
        return copy(self.__globals) if self.__globals else copy(DEFAULT_GLOBALS)

    @property
    def junos(self) -> dict[str, str | int]:
        return copy(self.__platforms.get('junos', DEFAULT_JUNOS))

    @property
    def ios(self) -> dict[str, str | int]:
        return copy(self.__platforms.get('ios', DEFAULT_IOS))

    @property
    def eos(self) -> dict[str, str | int]:
        return copy(self.__platforms.get('eos', DEFAULT_EOS))

    @property
    def nxos(self) -> dict[str, str | int]:
        return copy(self.__platforms.get('nxos', DEFAULT_NXOS))

    @property
    def styles(self) -> list[str]:
        return get_all_styles()

    @property
    def logger(self) -> logging.Logger:
        return self.__logger

    def __init__(self) -> None:
        self.__logger: logging.Logger = None
        self.__globals: dict[str, str | int] = {}
        self.__platforms: dict[str, dict[str, str | int]] = {}
        for platform in PLATFORMS:
            self.__platforms[platform] = {}
        self.__is_dir: bool = True
        self.__is_alert: bool = False
        self.__init_logging()
        self.__process_config()

    def __init_logging(self) -> None:
        errors: list[str] = []
        init_from_running: bool = False
        if os.path.exists(LOGGING_CONF):
            try:
                if sys.version_info.major == 3 and sys.version_info.minor >= 10:
                    fileConfig(LOGGING_CONF, encoding=LOGGING_CONF_ENCODING)
                else:
                    fileConfig(LOGGING_CONF)
            except Exception as err:
                err_msg = f'Error has occurred during the open of "{LOGGING_CONF}". '
                err_msg += 'Either does not exist or is not well-formatted. '
                err_msg += f'Exception: "{err}".'
                errors.append(err_msg)
                init_from_running = True
        else:
            init_from_running = True
            try:
                if not os.path.exists(LOGGING_CONF_DIR):
                    os.mkdir(LOGGING_CONF_DIR)
                with open(LOGGING_CONF, 'w', encoding=LOGGING_CONF_ENCODING) as f:
                    f.write(LOGGING_DEFAULTS)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as err:
                err_msg = f'Error has occurred during the creating of "{LOGGING_CONF}". '
                err_msg = f'Check the folder "{LOGGING_CONF_DIR}" is here and/or writable. '
                err_msg += f'Exception: "{err}".'
                errors.append(err_msg)
        self.__logger = logging.getLogger(__name__)
        if init_from_running:
            try:
                self.__logger.setLevel(logging.INFO)
                if not os.path.exists(LOGGING_FILE_DIR):
                    os.mkdir(LOGGING_FILE_DIR)
                formatter = logging.Formatter(LOGGING_FORMAT)
                file_handler = RotatingFileHandler(
                    filename=LOGGING_FILE,
                    maxBytes=LOGGING_FILE_MAX_SIZE_BYTES,
                    backupCount=LOGGING_FILE_MAX_INSTANCES,
                    encoding=LOGGING_FILE_ENCODING
                )
                file_handler.setFormatter(formatter)
                self.__logger.addHandler(file_handler)
            except Exception as err:
                err_msg = f'Error has occurred during the creating of "{LOGGING_FILE}". '
                err_msg += f'Check the folder "{LOGGING_FILE_DIR}" is here and/or writable. '
                err_msg += f'Exception: "{err}".'
                errors.append(err_msg)
        try:
            formatter = logging.Formatter(LOGGING_FORMAT)
            buf_handler = BufferingHandler(LOGGING_BUF_CAP)
            buf_handler.setFormatter(formatter)
            self.__logger.addHandler(buf_handler)
        except Exception as err:
            err_msg = 'Error has occurred during the creating of a memory log. '
            err_msg += f'Exception: "{err}".'
            errors.append(err_msg)
        if errors:
            self.__logger.info(f'Thymus {app_ver} started with errors.')
            for error in errors:
                self.__logger.error(error)
        else:
            self.__logger.info(f'Thymus {app_ver} started normally.')

    def __process_config(self) -> None:
        try:
            if not os.path.exists(SAVES_DIR):
                self.__logger.info(f'Creating a saves folder: {SAVES_DIR}.')
                os.mkdir(SAVES_DIR)
                os.mkdir(SCREENS_SAVES_DIR)
            else:
                if not os.path.exists(SCREENS_SAVES_DIR):
                    os.mkdir(SCREENS_SAVES_DIR)
                if not os.path.isdir(SAVES_DIR):
                    self.__logger.error(f'There is a path "{SAVES_DIR}", but it is not a folder.')
            if not os.path.exists(CONFIG_PATH):
                self.__logger.info(f'Creating a settings folder: {CONFIG_PATH}.')
                os.mkdir(CONFIG_PATH)
            else:
                if not os.path.isdir(CONFIG_PATH):
                    self.__is_dir = False
                    raise Exception(f'The path "{CONFIG_PATH}" exists, but it is not a folder.')
            if os.path.exists(f'{CONFIG_PATH}/{CONFIG_NAME}'):
                self.__logger.info(f'Init Thymus from: {CONFIG_NAME}.')
            else:
                self.__logger.info(f'There is no file: {CONFIG_NAME}. Init Thymus with defaults.')
                self.__save_config()
            self.__read_config()
        except Exception as err:
            self.__logger.error(f'{err}')
            self.__is_alert = True

    def __read_config(self) -> None:
        if not self.__is_dir:
            return
        self.__logger.debug(f'Loading a configuration from: {CONFIG_PATH}{CONFIG_NAME}.')
        data: dict[str, Any] = {}
        with open(f'{CONFIG_PATH}{CONFIG_NAME}', encoding='utf-8') as f:
            data = json.load(f)
            if not data:
                raise Exception(f'Reading of the config file "{CONFIG_NAME}" was failed.')
        self.validate_keys(DEFAULT_GLOBALS, data, self.__validate_globals)
        for platform, store in PLATFORMS.items():
            if platform_data := data.get(platform):
                if not hasattr(self, f'_AppSettings__validate_{platform}_key'):
                    self.__logger.error(f'No validator for {platform.upper()}. Default.')
                    continue
                validator = getattr(self, f'_AppSettings__validate_{platform}_key')
                self.validate_keys(store, platform_data, validator, platform)
            else:
                self.__logger.warning(f'No data for {platform.upper()}. Default.')

    def __save_config(self) -> None:
        if not self.__is_dir:
            return
        self.__logger.debug(f'Saving a configuration into the file: {CONFIG_PATH}{CONFIG_NAME}.')
        data = self.globals
        for platform, platform_data in PLATFORMS.items():
            data.update(
                {
                    platform: self.__platforms[platform] if self.__platforms.get(platform) else platform_data
                }
            )
        with open(f'{CONFIG_PATH}{CONFIG_NAME}', 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())

    def validate_keys(
            self,
            store: dict[str, str | int],
            data: dict[str, Any],
            validator: Callable[[str, str | int], int | str],
            platform: str = ''
    ) -> list[str]:
        errors: list[str] = []
        for key in store:
            # run through all over the available keys
            try:
                if value := data.get(key):
                    # if there is a value in the data for a key from the store
                    # we must check it with the callback
                    if type(value) is not str and type(value) is not int:
                        raise Exception(f'Validation error, value type mismatch: {key}->{type(value)}. Default.')
                    value = validator(key, value)
                    if platform:
                        self.__platforms[platform][key] = value
                    else:
                        self.__globals[key] = value
                else:
                    err_msg: str = ''
                    if platform:
                        err_msg = f'No data for "{key}" {platform} attribute. Default.'
                        self.__platforms[platform][key] = store[key]
                    else:
                        err_msg = f'No data for "{key}" global attribute. Default.'
                        self.__globals[key] = store[key]
                    self.__logger.error(err_msg)
                    errors.append(err_msg)
            except Exception:
                # makes it default
                err_msg: str = ''
                if platform:
                    err_msg = f'Incorrect value for the global attribute "{key}": {value}.'
                    self.__platforms[platform][key] = store[key]
                else:
                    self.__globals[key] = store[key]
                    err_msg = f'Incorrect value for the {platform.upper()} platform attribute '
                    err_msg += f'"{key}": {value}. Default.'
                self.__logger.error(err_msg)
                errors.append(err_msg)
        return errors

    def __validate_globals(self, key: str, value: str | int) -> str | int:
        if key == 'theme':
            if value not in self.styles:
                raise Exception
        elif key == 'filename_len':
            value = int(value)
            if value <= 0 or value > N_VALUE_LIMIT:
                raise Exception
        elif key == 'sidebar_limit':
            value = int(value)
            if value <= 0 or value > N_VALUE_LIMIT:
                raise Exception
        elif key == 'sidebar_strict_on_tab':
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self.__logger.warning(f'Unknown global attribute: {key}. Ignore.')
        return value

    def __validate_junos_key(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        else:
            self.__logger.warning(f'Unknown JunOS attribute: {key}. Ignore.')
        return value

    def __validate_ios_key(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'promisc', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self.__logger.warning(f'Unknown IOS attribute: {key}. Ignore.')
        return value

    def __validate_eos_key(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'promisc', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self.__logger.warning(f'Unknown EOS attribute: {key}. Ignore.')
        return value

    def __validate_nxos_key(self, key: str, value: str | int) -> str | int:
        if key == 'spaces':
            value = int(value)
            if value <= 0:
                raise Exception
        elif key in ('heuristics', 'crop', 'base_heuristics'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        else:
            self.__logger.warning(f'Unknown NXOS attribute: {key}. Ignore.')
        return value

    def is_bool_set(self, key: str, *, attr_name: str = 'globals') -> bool:
        '''
        Be careful! This method considers any integers except 1 as False. 1 is considered as True.
        If there is no key or no attribute method returns False!
        '''
        if not hasattr(self, attr_name):
            return False
        attr: dict[str, str | int] = getattr(self, attr_name)
        if key not in attr or not attr[key]:
            return False
        return attr[key] in (1, '1', 'on')

    def process_command(self, command: str) -> SettingsResponse:
        if not command.startswith('global '):
            return SettingsResponse.error('Unknown global command.')
        parts = command.split()
        if len(parts) < 3:
            return SettingsResponse.error('Incomplete global command.')
        subcommand = parts[1]
        if subcommand == 'show':
            if len(parts) > 4:
                return SettingsResponse.error('Too many arguments for "global show" command.')
            arg = parts[2]
            if arg == 'themes':
                if len(parts) == 4:
                    return SettingsResponse.error(f'Too many arguments for "global show {arg}" command.')
                result: list[str] = []
                result.append('* -- current theme')
                for theme in self.styles:
                    result.append(f'{theme}*' if theme == self.globals['theme'] else theme)
                return SettingsResponse.success(result)
            elif arg in ('filename_len', 'sidebar_limit'):
                if len(parts) == 4:
                    return SettingsResponse.error(f'Too many arguments for "global show {arg}" command.')
                result: int = self.globals[arg]
                return SettingsResponse.success(str(result))
            elif arg == 'sidebar_strict_on_tab':
                if len(parts) == 4:
                    return SettingsResponse.error(f'Too many arguments for "global show {arg}" command.')
                result: bool = self.is_bool_set(arg)
                return SettingsResponse.success(str(result))
            elif arg in PLATFORMS:
                if len(parts) == 4:
                    subarg = parts[3]
                    if subarg in ('default', 'defaults'):
                        return SettingsResponse.success(iter(f'{k}: {v}' for k, v in PLATFORMS[arg].items()))
                    else:
                        return SettingsResponse.error(
                            f'Unknown sub-argument for "global show {arg}" command: {subarg}.'
                        )
                else:
                    if self.__is_alert:
                        return SettingsResponse.error('These settings are default. App started abnormally.')
                    if not self.__platforms[arg]:
                        return SettingsResponse.success(iter(f'{k}: {v}' for k, v in PLATFORMS[arg].items()))
                    return SettingsResponse.success(iter(f'{k}: {v}' for k, v in self.__platforms[arg].items()))
            else:
                return SettingsResponse.error(f'Unknown argument for "global show" command: {arg}.')
        elif subcommand == 'set':
            if self.__is_alert:
                return SettingsResponse.error('The settings system is in read-only mode. App started abnormally.')
            if len(parts) < 4:
                return SettingsResponse.error('Incomplete "global set" command.')
            arg = parts[2]
            if arg == 'theme':
                if len(parts) > 4:
                    return SettingsResponse.error('Too many arguments for "global set" command.')
                value = parts[3]
                if value not in self.styles:
                    return SettingsResponse.error(f'Unsupported theme: {value}.')
                self.__globals[arg] = value
                self.__save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg in ('filename_len', 'sidebar_limit'):
                if len(parts) > 4:
                    return SettingsResponse.error(f'Too many arguments for "global set {arg}" command.')
                value = parts[3]
                if not value.isdigit() or int(value) <= 0 or int(value) > N_VALUE_LIMIT:
                    return SettingsResponse.error(f'Value must be in (0; {N_VALUE_LIMIT}].')
                self.__globals[arg] = int(value)
                self.__save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg == 'sidebar_strict_on_tab':
                if len(parts) > 4:
                    return SettingsResponse.error(f'Too many arguments for "global set {arg}" command.')
                value = parts[3]
                if value not in ('0', '1', 'on', 'off', 0, 1):
                    raise SettingsResponse.error('Value must be in (0, 1, on, off).')
                self.__globals[arg] = value
                self.__save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg in PLATFORMS:
                if len(parts) != 5:
                    return SettingsResponse.error(f'Incorrent number of arguments for "global set {arg}" command.')
                subarg = parts[3]
                if subarg not in PLATFORMS[arg]:
                    return SettingsResponse.error(
                        f'Unknown sub-argument for "global set {arg}" command: {subarg}.'
                    )
                value = parts[4]
                if not hasattr(self, f'_AppSettings__validate_{arg}_key'):
                    self.__logger.error(f'No validator for {arg}.')
                    return SettingsResponse.error('Unknown error. See the log file.')
                validator = getattr(self, f'_AppSettings__validate_{arg}_key')
                r = self.validate_keys({subarg: PLATFORMS[arg][subarg]}, {subarg: value}, validator, arg)
                if r:
                    return SettingsResponse.error(r)
                self.__save_config()
                return SettingsResponse.success(f'Attribute "{subarg}" was changed to: {value}.')
            else:
                return SettingsResponse.error(f'Unknown argument for "global set" command: {arg}.')
        else:
            return SettingsResponse.error(f'Unknown global command: {subcommand}.')
