from __future__ import annotations

from typing import TYPE_CHECKING

from textual.app import App
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
    SCREENS_SAVES_DIR,
)
from .app_settings import AppSettings
from .tui.open_dialog import OpenDialog
from .tui.modals.quit_modal import QuitApp
from .tui.modals.contexts_modal import ContextListScreen
from .tui.modals.logs_modal import LogsScreen


if TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.events import Resize

    import logging


class TThymus(App):
    CSS_PATH = 'tui/styles/main.css'
    SCREENS = {
        'open_file': OpenDialog()
    }
    BINDINGS = [
        ('ctrl+o', 'push_screen(\'open_file\')', 'Open File'),
        ('ctrl+n', 'night_mode', 'Night Mode'),
        ('ctrl+c', 'request_quit', 'Exit'),
        ('ctrl+s', 'request_contexts', 'Switch Contexts'),
        ('ctrl+l', 'request_logs', 'Show Logs'),
        ('ctrl+p', 'screenshot', 'Screenshot'),
    ]
    working_screens: var[list[str]] = var([])
    settings: var[AppSettings] = var(AppSettings())
    logger: var[logging.Logger] = var(None)
    is_logo_downscaled: var[bool] = var(False)
    logo: var[Static] = var(None)

    def __scale_logo(self, is_down: bool) -> None:
        try:
            text = f'Thymus {app_ver}' if is_down else WELCOME_TEXT.format(app_ver)
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

    def on_resize(self, event: Resize) -> None:
        if event.virtual_size.width <= WELCOME_TEXT_LEN and not self.is_logo_downscaled:
            self.__scale_logo(is_down=True)
        elif event.virtual_size.width > WELCOME_TEXT_LEN and self.is_logo_downscaled:
            self.__scale_logo(is_down=False)

    def action_request_quit(self) -> None:
        self.push_screen(QuitApp())

    def action_request_contexts(self) -> None:
        self.push_screen(ContextListScreen())

    def action_request_logs(self) -> None:
        self.push_screen(LogsScreen())

    def action_night_mode(self) -> None:
        self.dark = not self.dark

    def action_screenshot(self) -> None:
        try:
            self.save_screenshot(path=SCREENS_SAVES_DIR)
        except Exception as err:
            self.logger.error(f'Cannot save a screenshot: {err}.')
