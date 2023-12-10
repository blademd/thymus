from __future__ import annotations

import logging

from typing import TYPE_CHECKING, Optional

from textual.app import App, ComposeResult
from textual.widgets import (
    Footer,
    Static,
)
from textual.reactive import var
from rich.text import Text

from . import __version__ as app_ver
from . import (
    WELCOME_TEXT,
    WELCOME_TEXT_LEN,
    WRAPPER_DIR,
    SCREENS_DIR,
)
from .settings import AppSettings
from .tui import OpenDialog
from .tui.modals import (
    QuitApp,
    ContextListScreen,
    LogsScreen,
)

if TYPE_CHECKING:
    from textual.events import Resize


class TThymus(App):
    CSS_PATH = 'styles/main.css'
    SCREENS = {'open_file': OpenDialog()}
    BINDINGS = [
        ('ctrl+o', "push_screen('open_file')", 'Open File'),
        ('ctrl+n', 'night_mode', 'Night Mode'),
        ('ctrl+c', 'request_quit', 'Exit'),
        ('ctrl+s', 'request_contexts', 'Switch Contexts'),
        ('ctrl+l', 'request_logs', 'Show Logs'),
        ('ctrl+p', 'make_screenshot', 'Screenshot'),
    ]
    working_screens: var[list[str]] = var([])
    settings: var[AppSettings] = var(AppSettings())
    logger: var[logging.Logger] = var(logging.getLogger(__name__))
    is_logo_downscaled: var[bool] = var(False)
    logo: var[Optional[Static]] = var(None)

    def _scale_logo(self, is_down: bool) -> None:
        try:
            text = f'Thymus {app_ver}' if is_down else WELCOME_TEXT.format(app_ver)
            if self.logo:
                self.logo.update(Text(text, justify='center'))
            self.is_logo_downscaled = is_down
        except Exception as err:
            self.logger.debug(f'Logo downscaling error: {err}.')

    def compose(self) -> ComposeResult:
        yield Footer()
        yield Static(Text(WELCOME_TEXT.format(app_ver), justify='center'), id='main-welcome-out')

    def on_ready(self) -> None:
        self.logger = self.settings.logger
        self.logo = self.query_one('#main-welcome-out', Static)
        if self.settings.current_settings['night_mode'] in (0, '0', 'off'):
            self.dark = False

    def on_resize(self, event: Resize) -> None:
        if event.virtual_size.width <= WELCOME_TEXT_LEN and not self.is_logo_downscaled:
            self._scale_logo(is_down=True)
        elif event.virtual_size.width > WELCOME_TEXT_LEN and self.is_logo_downscaled:
            self._scale_logo(is_down=False)

    def action_request_quit(self) -> None:
        self.push_screen(QuitApp())

    def action_request_contexts(self) -> None:
        self.push_screen(ContextListScreen())

    def action_request_logs(self) -> None:
        self.push_screen(LogsScreen())

    def action_night_mode(self) -> None:
        self.dark = not self.dark
        if self.settings.current_settings['night_mode'] in (0, '0', 'off'):
            self.settings.process_command('global set night_mode on')
        else:
            self.settings.process_command('global set night_mode off')

    def action_make_screenshot(self) -> None:
        import os

        try:
            wrapper_path = os.path.expanduser(WRAPPER_DIR)
            screens_path = os.path.join(wrapper_path, SCREENS_DIR)
            self.save_screenshot(path=screens_path)
        except Exception as err:
            self.logger.error(f'Cannot save a screenshot: {err}.')
