from __future__ import annotations

import os
import json
import logging

from collections.abc import Iterator
from typing import Any, TYPE_CHECKING
from logging.handlers import RotatingFileHandler, BufferingHandler

from pygments.styles import get_all_styles  # type: ignore


from thymus import __version__ as app_ver
from thymus.settings import Setting, IntSetting, StrSetting, BoolSetting


if TYPE_CHECKING:
    from thymus.settings import Platform


class AppSettings:
    settings: dict[str, Setting] = {
        'config_version': IntSetting(2, fixed_values=(2,), show=False),
        'config_folder': StrSetting('settings', show=False, read_only=True),
        'config_name': StrSetting('thymus.json', show=False, read_only=True),
        'context_help': StrSetting('context_help.json', show=False, read_only=True),
        'wrapper_folder': StrSetting('~/thymus_data', show=False, read_only=True),
        'templates_folder': StrSetting('templates', show=False, read_only=True),
        'system_encoding': StrSetting('UTF-8', encoding=True),
        'last_opened_platform': StrSetting('', show=False),
        'default_folder': StrSetting('~/thymus_data/saves', description='default path for the open dialog'),
        'saves_folder': StrSetting('saves'),
        'screens_folder': StrSetting('screenshots'),
        'logging_folder': StrSetting('log'),
        'logging_level': StrSetting('DEBUG', fixed_values=('CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG')),
        'logging_file': StrSetting('thymus.log'),
        'logging_max_files': IntSetting(5, non_zero=True, negative=False),
        'logging_buffer_capacity': IntSetting(
            65535,
            non_zero=True,
            negative=False,
            description='number of records for memory buffering',
        ),
        'logging_default_format': StrSetting('%(asctime)s %(levelname)s %(message)s'),
        'theme': StrSetting(
            'pastie',
            description='some themes are better with the night mode',
            fixed_values=tuple(get_all_styles()),
        ),
        'night_mode': BoolSetting(False),
        'filename_max_length': IntSetting(256, val_range=(32, 1024)),
        'sidebar_max_length': IntSetting(64, val_range=(8, 1024)),
        'network_connection_timeout': IntSetting(15, val_range=(0, 1000), description='in seconds'),
        'editor_frequency_factor': IntSetting(4, fixed_values=(2, 4, 8, 10), description='devided by ten'),
        'editor_scale_factor': IntSetting(2, val_range=(1, 4), description='multiplied by the current height'),
        'save_on_commit': BoolSetting(False),
    }
    platforms: dict[str, Platform] = {}

    def __init__(self) -> None:
        self.alert = False
        self.init_in_memory_logging()
        self.init_main_folders()
        self.load()
        self.init_platforms()
        self.init_rest_folders()
        self.init_file_logging()

        if not self.alert:
            self.logger.info(f'Thymus {app_ver} started normally.')
        else:
            self.logger.info(f'Thymus {app_ver} started with errors. System is in the read-only mode.')

    def __iter__(self) -> Iterator[tuple[str, Setting]]:
        yield from self.settings.items()

    def __getitem__(self, key: str) -> Setting:
        return self.settings[key]

    def _check_folder(self, path: str) -> bool:
        if os.path.exists(path):
            if not os.path.isdir(path):
                self.logger.error(f'The path "{path}" exits, but it is not a folder!')
                return False
        else:
            try:
                os.mkdir(path)
                self.logger.debug(f'The "{path}" was created.')
            except Exception as error:
                self.logger.debug(f'An error has occurred during the "{path}" creation: {error}.')
                return False

        return True

    def init_in_memory_logging(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(self.settings['logging_level'].value)

        buf_handler = BufferingHandler(self.settings['logging_buffer_capacity'].value)
        buf_handler.setFormatter(logging.Formatter(self.settings['logging_default_format'].value))

        self.logger.addHandler(buf_handler)

    def init_main_folders(self) -> None:
        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
        settings_path = os.path.join(pre_path, self.settings['config_folder'].value)

        if not self._check_folder(pre_path):
            self.alert = True

        if not self._check_folder(settings_path):
            self.alert = True

    def load(self) -> None:
        if self.alert:
            self.logger.error('Cannot load conifg, system is in the read-only mode.')
            return

        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
        path = os.path.join(
            pre_path,
            self.settings['config_folder'].value,
            self.settings['config_name'].value,
        )

        if os.path.exists(path):
            if os.path.isfile(path):
                try:
                    with open(path, encoding=self.settings['system_encoding'].value) as f:
                        data: dict = json.load(f)
                        if not data:
                            raise Exception(f'The file "{path}" is empty or cannot be read.')

                        config_version = data.get('config_version')
                        if not config_version or config_version != 2:
                            self.logger.error('Current version of config is not compatible. Purging it.')
                            self.dump()
                        else:
                            self.bootstrap_settings(data)
                except Exception as error:
                    err_msg = f'Error has occurred during reading of "{path}". '
                    err_msg += f'Exception: "{error}". System now is in the read-only mode!'
                    self.logger.error(err_msg)
                    self.alert = True
            else:
                self.logger.error(f'The path "{path}" is not a file. System now is in the read-only mode!')
                self.alert = True
        else:
            # The system config file does not exist, so we need to create it
            self.dump()

    def init_platforms(self) -> None:
        if self.alert:
            self.logger.error('Cannot init platforms, system is in the read-only mode.')
            return

        from thymus.settings import PLATFORMS, PlatformLoadFail

        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
        settings_path = os.path.join(pre_path, self.settings['config_folder'].value)

        for name, platform_type in PLATFORMS:
            platform_conf = os.path.join(settings_path, name + '.json')
            platform = platform_type(platform_conf, load=False)

            try:
                platform.load()
                self.platforms[name] = platform
            except PlatformLoadFail as error:
                err_msg = f'Cannot load platform config for "{name}". '
                err_msg += f'Exception: "{error}".'
                self.logger.error(err_msg)

            self.platforms[name] = platform

    def init_rest_folders(self) -> None:
        if self.alert:
            self.logger.error('Cannot init rest folders, system is in the read-only mode.')
            return

        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)

        saves_path = os.path.join(pre_path, self.settings['saves_folder'].value)
        self._check_folder(saves_path)

        screens_path = os.path.join(pre_path, self.settings['screens_folder'].value)
        self._check_folder(screens_path)

    def init_file_logging(self) -> None:
        if self.alert:
            self.logger.error('Cannot init logging to file, system is in the read-only mode.')
            return

        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
        path = os.path.join(pre_path, self.settings['logging_folder'].value)

        if not self._check_folder(path):
            self.logger.error(f'Cannot init loggin to file, "{path}" is unavailable.')
            return

        log_file = os.path.join(path, self.settings['logging_file'].value)

        self.logger.setLevel(self.settings['logging_level'].value)

        try:
            file_handler = RotatingFileHandler(
                filename=log_file,
                maxBytes=self.settings['logging_file_max_size'].value,
                backupCount=self.settings['logging_max_files'].value,
                encoding=self.settings['system_encoding'].value,
            )
            file_handler.setFormatter(logging.Formatter(self.settings['logging_default_format'].value))
            self.logger.addHandler(file_handler)

        except Exception as error:
            err_msg = 'Error has occurred during the file logging start. '
            err_msg += f'Exception: "{error}".'
            self.logger.error(err_msg)
        else:
            # If everything is fine we need to fill the file log with values from the memory log
            for handler in self.logger.handlers:
                if type(handler) is not BufferingHandler:
                    continue
                for record in handler.buffer:
                    file_handler.emit(record)
            self.logger.debug('File logging started.')

    def bootstrap_settings(self, data: dict[str, Any]) -> None:
        if self.alert:
            self.logger.error('Cannot bootstrap settings from the config, system is in the read-only mode.')
            return

        for k, v in data.items():
            if not self.settings.get(k):
                self.logger.warning(f'Unknown settings key: {k}. Ignoring.')
                continue

            setting = self.settings[k]

            try:
                setting.value = v
            except Exception as error:
                err_msg = str(error)
                err_msg = err_msg.replace('..', '.')
                self.logger.error(f'Cannot apply the setting "{k}": {err_msg}.')

    def dump(self) -> None:
        if self.alert:
            self.logger.error('Cannot save conifg, system is in the read-only mode.')
            return

        try:
            pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
            path = os.path.join(
                pre_path,
                self.settings['config_folder'].value,
                self.settings['config_name'].value,
            )
            with open(path, 'w', encoding='utf-8') as f:
                data: dict[str, Any] = {}
                for k, v in self.settings.items():
                    if v.read_only:
                        continue
                    data[k] = v.value
                json.dump(data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as error:
            err_msg = f'Error has occurred during saving of "{path}". '
            err_msg += f'Exception: "{error}".'
            err_msg += 'System now is in the read-only mode!'
            self.logger.error(err_msg)
            self.alert = True

    def where_to_save(self) -> str:
        if self.alert:
            return ''

        pre_path = os.path.expanduser(self.settings['wrapper_folder'].value)
        path = os.path.join(pre_path, self.settings['saves_folder'].value)

        return path

    def update_last_opened_platform(self, platform: Platform) -> None:
        for k, v in self.platforms.items():
            if platform is v:
                break
        else:
            return

        try:
            self.settings['last_opened_platform'].value = k
            self.dump()
        except (KeyError, ValueError):
            return
