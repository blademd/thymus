from __future__ import annotations

import os
import json
import logging

from typing import Any, cast
from logging.handlers import RotatingFileHandler, BufferingHandler

from pygments.styles import get_all_styles  # type: ignore

from .. import __version__ as app_ver
from .. import (
    CONFIG_PATH,
    CONFIG_NAME,
    LOGGING_FILE,
    LOGGING_FILE_DIR,
    LOGGING_FORMAT,
    LOGGING_CONF,
    LOGGING_CONF_ENCODING,
    LOGGING_FILE_MAX_SIZE_BYTES,
    LOGGING_FILE_MAX_INSTANCES,
    LOGGING_FILE_ENCODING,
    LOGGING_BUF_CAP,
    N_VALUE_LIMIT,
    SAVES_DIR,
    SCREENS_DIR,
    WRAPPER_DIR,
    NET_TIMEOUT_LIMIT,
)
from ..responses import Response, SettingsResponse
from .platform import (
    Platform,
    JunosPlatform,
    IOSPlatform,
    EOSPlatform,
    NXOSPlatform,
)


def check_folder(path: str, *, logger: logging.Logger) -> bool:
    if os.path.exists(path):
        if not os.path.isdir(path):
            logger.error(f'The path "{path}" exits, but it is not a folder!')
            return False
    else:
        try:
            os.mkdir(path)
            logger.debug(f'The "{path}" was created.')
        except Exception as error:
            logger.error(f'An error has occurred during the "{path}" creation: {error}.')
            return False
    return True


class AppSettings:
    __slots__ = (
        '_platforms',
        '_logger',
        '_is_alert',
    )
    settings: dict[str, str | int] = {
        'theme': 'monokai',
        'night_mode': 'off',
        'filename_len': 256,
        'sidebar_limit': 64,
        'sidebar_strict_on_tab': 'on',
        'open_dialog_platform': 'junos',
        'default_folder': os.path.join(WRAPPER_DIR, SAVES_DIR),
        'network_timeout': 15,
    }
    current_settings: dict[str, str | int] = {}

    @property
    def logger(self) -> logging.Logger:
        """For external access, e.g., from tui.py."""
        return self._logger

    @property
    def platforms(self) -> dict[str, Platform]:
        """For external access, e.g. from open_dialog.py."""
        return self._platforms

    def __init__(self) -> None:
        self._platforms: dict[str, Platform] = {}
        self._is_alert = False
        self.init_mem_logging()  # must be first
        self.load_defaults()
        self.init_folders()
        if not self._is_alert and self.read_config():
            self.init_file_logging()
            self._logger.info(f'Thymus {app_ver} started normally.')
        else:
            self._logger.info(f'Thymus {app_ver} started with errors. It is a read-only mode.')

    def load_defaults(self) -> None:
        for k, v in self.settings.items():
            self.current_settings[k] = v
        # REGISTER ALL POSSIBLE PLATFORMS HERE
        self._platforms = {
            'junos': JunosPlatform(logger=self._logger),
            'ios': IOSPlatform(logger=self._logger),
            'nxos': NXOSPlatform(logger=self._logger),
            'eos': EOSPlatform(logger=self._logger),
        }

    def init_mem_logging(self) -> None:
        self._logger = logging.getLogger(__name__)
        self._logger.setLevel(logging.INFO)
        formatter = logging.Formatter(LOGGING_FORMAT)
        buf_handler = BufferingHandler(LOGGING_BUF_CAP)
        buf_handler.setFormatter(formatter)
        self._logger.addHandler(buf_handler)
        self._logger.debug('Memory logging started.')

    def init_folders(self) -> None:
        wrapper_path = os.path.expanduser(WRAPPER_DIR)
        if not check_folder(wrapper_path, logger=self._logger):
            self._is_alert = True
            return
        settings_path = os.path.join(wrapper_path, CONFIG_PATH)
        if not check_folder(settings_path, logger=self._logger):
            self._is_alert = True
            return
        logs_path = os.path.join(wrapper_path, LOGGING_FILE_DIR)
        check_folder(logs_path, logger=self._logger)
        saves_path = os.path.join(wrapper_path, SAVES_DIR)
        check_folder(saves_path, logger=self._logger)
        screens_path = os.path.join(wrapper_path, SCREENS_DIR)
        check_folder(screens_path, logger=self._logger)

    def init_file_logging(self) -> None:
        wrapper_path = os.path.expanduser(WRAPPER_DIR)
        log_conf_path = os.path.join(wrapper_path, LOGGING_CONF)
        data = {}
        default_config = {
            'level': 'INFO',
            'format': LOGGING_FORMAT,
            'filename': os.path.join(wrapper_path, LOGGING_FILE),
            'max_size_bytes': LOGGING_FILE_MAX_SIZE_BYTES,
            'max_files': LOGGING_FILE_MAX_INSTANCES,
            'encoding': LOGGING_FILE_ENCODING,
        }
        if not os.path.exists(log_conf_path):
            # If the logging config file does not exist we try to create if first
            try:
                with open(log_conf_path, 'w', encoding=LOGGING_CONF_ENCODING) as f:
                    json.dump(default_config, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
            except Exception as error:
                err_msg = f'Error has occurred during the creating of "{log_conf_path}". '
                err_msg += f'Exception: "{error}".'
                self._logger.error(err_msg)
        else:
            # If it is here, check whether it is dir or not
            if not os.path.isdir(log_conf_path):
                # Try to open it and fill the data with its settings
                f = open(log_conf_path, encoding='utf-8')
                data = json.load(f)
                if not data:
                    self._logger.error(f'The file "{log_conf_path}" is empty or cannot be read.')
            else:
                self._logger.error(f'The path "{log_conf_path}" is a directory.')
        try:
            # This sections tryes to start file logging
            # It uses either the data which contains settings from the config file or the default settings
            level_val = data.get('level', default_config['level'])
            logging_level = logging.INFO
            if level_val == 'ERROR':
                logging_level = logging.ERROR
            elif level_val == 'WARNING':
                logging_level = logging.WARNING
            elif level_val == 'DEBUG':
                logging_level = logging.DEBUG
            self._logger.setLevel(logging_level)  # reset the log-level
            format_val = data.get('format', default_config['format'])
            formatter = logging.Formatter(format_val)
            file_handler = RotatingFileHandler(
                filename=data.get('filename', default_config['filename']),
                maxBytes=int(data.get('max_size_bytes', default_config['max_size_bytes'])),
                backupCount=int(data.get('max_files', default_config['max_files'])),
                encoding=data.get('encoding', default_config['encoding']),
            )
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)
        except Exception as error:
            err_msg = 'Error has occurred during the file logging start. '
            err_msg += f'Exception: "{error}".'
            self._logger.error(err_msg)
        else:
            # If everything is fine we need to fill the file log with values from the memory log
            for handler in self._logger.handlers:
                if type(handler) is not BufferingHandler:
                    continue
                for record in handler.buffer:
                    file_handler.emit(record)
            self._logger.debug('File logging started.')

    def read_config(self) -> bool:
        wrapper_path = os.path.expanduser(WRAPPER_DIR)
        conf_file_path = os.path.join(wrapper_path, CONFIG_PATH, CONFIG_NAME)
        if os.path.exists(conf_file_path):
            # If the config file path exists
            if os.path.isfile(conf_file_path):
                # Make sure that it is a file and try to open
                try:
                    f = open(conf_file_path, encoding='utf-8')
                    data = json.load(f)
                    if not data:
                        # We do not try to delete the file and re-create it properly, leaving the decision for the user
                        raise Exception(f'The file "{conf_file_path}" is empty or cannot be read.')
                    # Bootstrap the system and the platforms settings
                    self.bootstrap_settings(data)
                    for platform in self._platforms:
                        if platform_data := data.get(platform):
                            self.bootstrap_settings(platform_data, platform=platform)
                        else:
                            self._logger.warning(f'No data for {platform.upper()}. Default platform data selected.')
                except Exception as error:
                    err_msg = f'Error has occurred during reading of "{conf_file_path}". '
                    err_msg += f'Exception: "{error}".'
                    self._logger.error(err_msg)
                    self._is_alert = True
                    return False
            else:
                self._logger.error(f'The path "{conf_file_path}" is a directory.')
                self._is_alert = True
                return False
        else:
            # The system config file does not exist, so we need to create it
            # It is already filled with the default data thanks to the load_defaults() call
            result = self.save_config()
            self._is_alert = not result
            return result
        self._logger.debug(f'The config file "{conf_file_path}" was read.')
        return True

    def save_config(self) -> bool:
        wrapper_path = os.path.expanduser(WRAPPER_DIR)
        conf_file_path = os.path.join(wrapper_path, CONFIG_PATH, CONFIG_NAME)
        data: dict[str, str | int | dict[str, str | int]] = {}
        for k, v in self.current_settings.items():
            data[k] = v
        for platform, platform_obj in self._platforms.items():
            data.update({platform: platform_obj.current_settings})
        try:
            with open(conf_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as error:
            err_msg = f'Error has occurred during saving of "{conf_file_path}". '
            err_msg += f'Exception: "{error}".'
            self._logger.error(err_msg)
            return False
        self._logger.debug(f'System settings were saved to: {conf_file_path}.')
        return True

    def validate(self, key: str, value: str | int) -> str | int:
        if key == 'theme':
            if value not in get_all_styles():
                raise Exception
        elif key == 'filename_len':
            value = int(value)
            if value <= 0 or value > N_VALUE_LIMIT:
                raise Exception
        elif key == 'sidebar_limit':
            value = int(value)
            if value <= 0 or value > N_VALUE_LIMIT:
                raise Exception
        elif key == 'open_dialog_platform':
            if value not in self._platforms:
                raise Exception
        elif key in ('sidebar_strict_on_tab', 'night_mode'):
            if value not in ('0', '1', 'on', 'off', 0, 1):
                raise Exception
        elif key == 'default_folder':
            path = os.path.expanduser(str(value))
            if not os.path.exists(path) or not os.path.isdir(path):
                raise Exception
        elif key == 'network_timeout':
            value = int(value)
            if value <= 0 or value > NET_TIMEOUT_LIMIT:
                raise
        else:
            self._logger.warning(f'Unknown global attribute: {key}. Ignored.')
        return value

    def bootstrap_settings(self, data: Any, *, platform='') -> None:
        if type(data) is not dict:
            return
        obj = self.settings
        if platform:
            if platform not in self._platforms:
                return
            obj = self._platforms[platform].settings
        for key in obj:
            try:
                value = data.get(key, '')
                if not value:
                    err_msg = f'Validation error, an empty value for the "{key}" received.'
                    err_msg += ' Default value selected.'
                    self._logger.error(err_msg)
                    continue
                if type(value) is not str and type(value) is not int:
                    err_msg = f'Validation error, value type mismatch: {key}->{type(value)}.'
                    err_msg += ' Default value selected.'
                    self._logger.error(err_msg)
                    continue
                value = cast('str | int', value)
                if not platform:
                    value = self.validate(key, value)
                    self.current_settings[key] = value
                else:
                    value = self._platforms[platform].validate(key, value)
                    self._platforms[platform].current_settings[key] = value
            except Exception:
                err_msg = f'Validation key "{key}" failed. Default value selected.'
                self._logger.error(err_msg)

    def process_command(self, command: str) -> Response:
        if not command.startswith('global '):
            return SettingsResponse.error('Unknown global command.')
        parts = command.split()
        if len(parts) < 3:
            return SettingsResponse.error('Incomplete global command.')
        subcommand = parts[1]
        if subcommand == 'show':
            # GLOBALS
            if len(parts) > 4:
                return SettingsResponse.error('Too many arguments for "global show" command.')
            arg = parts[2]
            if arg == 'themes':
                if len(parts) == 4:
                    return SettingsResponse.error(f'Too many arguments for "global show {arg}" command.')
                themes_result = []
                themes_result.append('* -- current theme')
                for theme in get_all_styles():
                    themes_result.append(f'{theme}*' if theme == self.current_settings['theme'] else theme)
                return SettingsResponse.success(themes_result)
            elif arg in (
                'open_dialog_platform',
                'filename_len',
                'sidebar_limit',
                'sidebar_strict_on_tab',
                'night_mode',
                'default_folder',
                'network_timeout',
            ):
                if len(parts) == 4:
                    return SettingsResponse.error(f'Too many arguments for "global show {arg}" command.')
                return SettingsResponse.success(str(self.current_settings[arg]))
            # PLATFORMS FROM HERE
            elif arg in self._platforms:
                if len(parts) == 4:
                    subarg = parts[3]
                    if subarg in ('default', 'defaults'):
                        return SettingsResponse.success(
                            iter(f'{k}: {v}' for k, v in self._platforms[arg].settings.items())
                        )
                    else:
                        return SettingsResponse.error(
                            f'Unknown sub-argument for "global show {arg}" command: {subarg}.'
                        )
                else:
                    if self._is_alert:
                        return SettingsResponse.error('All settings are default. Thymus started abnormally.')
                    return SettingsResponse.success(
                        iter(f'{k}: {v}' for k, v in self._platforms[arg].current_settings.items())
                    )
            else:
                return SettingsResponse.error(f'Unknown argument for "global show" command: {arg}.')
        elif subcommand == 'set':
            # GLOBALS
            if self._is_alert:
                return SettingsResponse.error('System in read-only mode. Thymus started abnormally.')
            if len(parts) < 4:
                return SettingsResponse.error('Incomplete "global set" command.')
            arg = parts[2]
            if arg == 'theme':
                if len(parts) > 4:
                    return SettingsResponse.error('Too many arguments for "global set" command.')
                value = parts[3]
                if value not in get_all_styles():
                    return SettingsResponse.error(f'Unsupported theme: {value}.')
                self.current_settings[arg] = value
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg == 'open_dialog_platform':
                if len(parts) > 4:
                    return SettingsResponse.error('Too many arguments for "global set" command.')
                value = parts[3]
                if value not in self._platforms:
                    return SettingsResponse.error(f'Unsupported platform: {value}.')
                self.current_settings[arg] = value
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg in ('filename_len', 'sidebar_limit'):
                if len(parts) > 4:
                    return SettingsResponse.error(f'Too many arguments for "global set {arg}" command.')
                value = parts[3]
                if not value.isdigit() or int(value) <= 0 or int(value) > N_VALUE_LIMIT:
                    return SettingsResponse.error(f'Value must be in (0; {N_VALUE_LIMIT}].')
                self.current_settings[arg] = int(value)
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg in ('sidebar_strict_on_tab', 'night_mode'):
                if len(parts) > 4:
                    return SettingsResponse.error(f'Too many arguments for "global set {arg}" command.')
                value = parts[3]
                if value not in ('0', '1', 'on', 'off', 0, 1):
                    return SettingsResponse.error('Value must be in (0, 1, on, off).')
                self.current_settings[arg] = value
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg == 'default_folder':
                if len(parts) > 4:
                    return SettingsResponse.error('Too many arguments for "global set" command.')
                value = parts[3]
                path = os.path.expanduser(str(value))
                if not os.path.exists(path) or not os.path.isdir(path):
                    return SettingsResponse.error('Default directory does not exist.')
                self.current_settings[arg] = value
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            elif arg == 'network_timeout':
                if len(parts) > 4:
                    return SettingsResponse.error('Too many arguments for "global set" command.')
                value = parts[3]
                if not value.isdigit() or int(value) <= 0 or int(value) > NET_TIMEOUT_LIMIT:
                    return SettingsResponse.error(f'Value must be in (0; {NET_TIMEOUT_LIMIT}].')
                self.current_settings[arg] = int(value)
                self.save_config()
                return SettingsResponse.success(f'The "{arg}" was changed to: {value}.')
            # PLATFORMS FROM HERE
            elif arg in self._platforms:
                if len(parts) != 5:
                    return SettingsResponse.error(f'Incorrent number of arguments for "global set {arg}" command.')
                subarg = parts[3]
                if subarg not in self._platforms[arg].current_settings:
                    return SettingsResponse.error(f'Unknown sub-argument for "global set {arg}" command: {subarg}.')
                value = parts[4]
                try:
                    value = str(self._platforms[arg].validate(subarg, value))
                    self._platforms[arg].current_settings[subarg]
                except Exception:
                    return SettingsResponse.error(f'Cannot set the value for "{subarg}".')
                self.save_config()
                return SettingsResponse.success(f'Attribute "{subarg}" was changed to: {value}.')
            else:
                return SettingsResponse.error(f'Unknown argument for "global set" command: {arg}.')
        else:
            return SettingsResponse.error(f'Unknown global command: {subcommand}.')
